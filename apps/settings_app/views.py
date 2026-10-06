import json
from io import StringIO

from django.core.management import call_command
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import ModulePermission

from . import serializers as s
from .models import BusinessSettings, HardwareSettings, InvoiceSettings, PaymentSettings


class SingletonView(APIView):
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "settings"
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    model = None
    serializer_class = None

    def get(self, request):
        return Response(self.serializer_class(self.model.load(), context={"request": request}).data)

    def put(self, request):
        serializer = self.serializer_class(self.model.load(), data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    patch = put


class BusinessView(SingletonView):
    model, serializer_class = BusinessSettings, s.BusinessSerializer


class InvoiceView(SingletonView):
    model, serializer_class = InvoiceSettings, s.InvoiceSerializer


class PaymentView(SingletonView):
    model, serializer_class = PaymentSettings, s.PaymentSerializer


class HardwareView(SingletonView):
    model, serializer_class = HardwareSettings, s.HardwareSerializer


class PublicSettingsView(APIView):
    """Read-only bundle for the POS / receipt printing. Any signed-in user may read it."""

    def get(self, request):
        ctx = {"request": request}
        return Response(
            {
                "business": s.BusinessSerializer(BusinessSettings.load(), context=ctx).data,
                "invoice": s.InvoiceSerializer(InvoiceSettings.load(), context=ctx).data,
                "payment": s.PaymentSerializer(PaymentSettings.load(), context=ctx).data,
                "hardware": s.HardwareSerializer(HardwareSettings.load(), context=ctx).data,
            }
        )


class BackupView(APIView):
    """Downloads a JSON export of all application data (Django fixture format, restorable with loaddata)."""

    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "settings"
    permission_actions = {"get": "EXPORT"}

    def get(self, request):
        buffer = StringIO()
        call_command(
            "dumpdata", exclude=["contenttypes", "auth.permission", "sessions", "admin.logentry"],
            indent=1, stdout=buffer,
        )
        response = HttpResponse(buffer.getvalue(), content_type="application/json")
        stamp = timezone.localtime().strftime("%Y%m%d_%H%M%S")
        response["Content-Disposition"] = f'attachment; filename="wms_backup_{stamp}.json"'
        return response
