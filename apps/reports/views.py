import csv

from django.http import Http404, HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import ModulePermission
from apps.core.pagination import StandardPagination

from . import services

EXPORT_LIMIT = 50000


class ReportView(APIView):
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "reports"

    def get(self, request, name):
        report = services.REPORTS.get(name)
        if report is None:
            raise Http404
        rows, columns, summary = report(request.query_params)

        if request.query_params.get("export") == "csv":
            if not request.user.can("reports", "EXPORT"):
                return Response({"detail": "You do not have permission to perform this action."}, status=403)
            return self.csv(name, columns, rows)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(rows, request)
        response = paginator.get_paginated_response(page)
        response.data["columns"] = columns
        response.data["summary"] = summary
        return response

    @staticmethod
    def csv(name, columns, rows):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="report_{name}.csv"'
        writer = csv.writer(response)
        writer.writerow([c["label"] for c in columns])
        for i, row in enumerate(rows):
            if i >= EXPORT_LIMIT:
                break
            writer.writerow([row.get(c["key"]) for c in columns])
        return response


class DashboardView(APIView):
    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = "dashboard"

    def get(self, request):
        return Response(services.dashboard())
