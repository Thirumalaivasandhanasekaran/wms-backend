from rest_framework import mixins

from apps.core.viewsets import BaseViewSet

from .models import Sale, SalesReturn
from .serializers import SaleSerializer, SalesReturnSerializer


class AppendOnlyViewSet(BaseViewSet):
    http_method_names = ["get", "post", "head", "options"]


class SaleViewSet(AppendOnlyViewSet):
    queryset = Sale.objects.select_related("customer", "created_by").prefetch_related(
        "items__variant__product", "items__variant__size", "items__variant__colour", "payments"
    )
    serializer_class = SaleSerializer
    permission_module = "pos"
    search_fields = ["invoice_no", "customer__name", "customer__mobile"]
    filter_fields = ["customer", "status", ("payment_method", "payments__method")]
    date_field = "date"
    date_is_datetime = True
    export_name = "sales"


class SalesReturnViewSet(AppendOnlyViewSet):
    queryset = SalesReturn.objects.select_related("sale", "customer").prefetch_related("items__variant__product", "items__variant__size", "items__variant__colour")
    serializer_class = SalesReturnSerializer
    permission_module = "sales_return"
    search_fields = ["return_no", "sale__invoice_no", "customer__name", "reason"]
    filter_fields = ["customer", "refund_method", "status"]
    date_field = "date"
    export_name = "sales_returns"
