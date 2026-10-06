from django.db.models import Q

from apps.core.viewsets import BaseViewSet

from .models import StockAdjustment, StockIn, StockMovement, StockOut
from .serializers import StockAdjustmentSerializer, StockInSerializer, StockMovementSerializer, StockOutSerializer


class DocumentViewSet(BaseViewSet):
    """Stock documents are append-only: corrections are made with a Stock Adjustment, never by editing history."""

    http_method_names = ["get", "post", "head", "options"]
    date_field = "date"

    def get_queryset(self):
        qs = super().get_queryset()
        variant = self.request.query_params.get("variant")
        return qs.filter(items__variant_id=variant).distinct() if variant else qs


class StockInViewSet(DocumentViewSet):
    queryset = StockIn.objects.select_related("supplier", "warehouse", "zone", "rack", "bin").prefetch_related("items__variant__product", "items__variant__size", "items__variant__colour")
    serializer_class = StockInSerializer
    permission_module = "stock_in"
    search_fields = ["document_no", "supplier__name", "batch_reference", "items__variant__sku", "items__variant__product__name"]
    filter_fields = ["supplier", "warehouse"]
    export_name = "stock_in"


class StockOutViewSet(DocumentViewSet):
    queryset = StockOut.objects.select_related("warehouse").prefetch_related("items__variant__product", "items__variant__size", "items__variant__colour")
    serializer_class = StockOutSerializer
    permission_module = "stock_out"
    search_fields = ["document_no", "remarks", "items__variant__sku", "items__variant__product__name"]
    filter_fields = ["warehouse", "reason"]
    export_name = "stock_out"


class StockAdjustmentViewSet(DocumentViewSet):
    queryset = StockAdjustment.objects.select_related("warehouse").prefetch_related("items__variant__product", "items__variant__size", "items__variant__colour")
    serializer_class = StockAdjustmentSerializer
    permission_module = "stock_adjustment"
    search_fields = ["document_no", "reason", "approved_by", "items__variant__sku", "items__variant__product__name"]
    filter_fields = ["warehouse", "adjustment_type"]
    export_name = "stock_adjustments"


class StockMovementViewSet(BaseViewSet):
    """Read-only audit trail of every stock change."""

    http_method_names = ["get", "head", "options"]
    queryset = StockMovement.objects.select_related("variant__product", "warehouse", "created_by")
    serializer_class = StockMovementSerializer
    permission_module = "reports"
    search_fields = ["variant__sku", "variant__barcode", "variant__product__name", "reference_no"]
    filter_fields = ["variant", "warehouse", "movement_type"]
    date_field = "created_at"
    date_is_datetime = True
    export_name = "stock_movements"
