import csv

from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import ModulePermission

EXPORT_LIMIT = 50000


def csv_response(filename, headers, rows):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response


class BaseViewSet(viewsets.ModelViewSet):
    """Server-side search, exact filters, ordering, pagination, CSV export and module permissions."""

    permission_classes = [IsAuthenticated, ModulePermission]
    permission_module = None
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = []
    # query-param names mapped to ORM lookups; a plain string uses the same name for both.
    filter_fields = []
    ordering_fields = "__all__"
    ordering = ["-id"]
    export_name = "export"
    date_field = None  # set to enable ?date_from= / ?date_to= filtering
    date_is_datetime = False

    def get_queryset(self):
        qs = super().get_queryset()
        if self.date_field:
            suffix = "__date" if self.date_is_datetime else ""
            for param, op in (("date_from", "gte"), ("date_to", "lte")):
                value = self.request.query_params.get(param)
                if value:
                    qs = qs.filter(**{f"{self.date_field}{suffix}__{op}": value})
        for item in self.filter_fields:
            param, lookup = item if isinstance(item, tuple) else (item, item)
            value = self.request.query_params.get(param)
            if value not in (None, ""):
                qs = qs.filter(**{lookup: value})
        return qs

    def perform_create(self, serializer):
        if hasattr(serializer.Meta.model, "created_by"):
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()

    @action(detail=False, methods=["get"])
    def export(self, request):
        qs = self.filter_queryset(self.get_queryset())[:EXPORT_LIMIT]
        data = self.get_serializer(qs, many=True).data
        if not data:
            return csv_response(f"{self.export_name}.csv", [], [])
        keys = [k for k, v in data[0].items() if not isinstance(v, (dict, list))]
        rows = [[row.get(k) for k in keys] for row in data]
        return csv_response(f"{self.export_name}.csv", keys, rows)
