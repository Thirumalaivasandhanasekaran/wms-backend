from django.db.models import Count, IntegerField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.viewsets import BaseViewSet

from . import models as m
from . import serializers as s


class WarehouseViewSet(BaseViewSet):
    queryset = m.Warehouse.objects.all()
    serializer_class = s.WarehouseSerializer
    permission_module = "warehouse"
    search_fields = ["name", "address", "location", "pincode", "contact_person", "phone", "email"]
    filter_fields = ["status", "warehouse_type"]
    export_name = "warehouses"


class ZoneViewSet(BaseViewSet):
    queryset = m.Zone.objects.select_related("warehouse")
    serializer_class = s.ZoneSerializer
    permission_module = "zone"
    search_fields = ["name", "description", "warehouse__name"]
    filter_fields = ["status", "warehouse"]
    export_name = "zones"


class RackViewSet(BaseViewSet):
    queryset = m.Rack.objects.select_related("warehouse", "zone")
    serializer_class = s.RackSerializer
    permission_module = "rack"
    search_fields = ["name", "code", "description", "warehouse__name", "zone__name"]
    filter_fields = ["status", "warehouse", "zone"]
    export_name = "racks"


class BinViewSet(BaseViewSet):
    queryset = m.Bin.objects.select_related("warehouse", "zone", "rack")
    serializer_class = s.BinSerializer
    permission_module = "bin"
    search_fields = ["name", "code", "warehouse__name", "zone__name", "rack__name"]
    filter_fields = ["status", "warehouse", "zone", "rack"]
    export_name = "bins"


class MaterialViewSet(BaseViewSet):
    queryset = m.Material.objects.select_related("category", "unit")
    serializer_class = s.MaterialSerializer
    permission_module = "material"
    search_fields = ["material_code", "material_name", "description", "category__name"]
    filter_fields = ["status", "category", "unit"]
    export_name = "materials"


class UnitViewSet(BaseViewSet):
    queryset = m.Unit.objects.all()
    serializer_class = s.UnitSerializer
    permission_module = "uom"
    search_fields = ["name", "short_name"]
    filter_fields = ["status"]
    export_name = "uom"


class CategoryViewSet(BaseViewSet):
    queryset = m.Category.objects.all()
    serializer_class = s.CategorySerializer
    permission_module = "category"
    search_fields = ["name", "description"]
    filter_fields = ["status"]
    export_name = "categories"


class CustomerViewSet(BaseViewSet):
    queryset = m.Customer.objects.all()
    serializer_class = s.CustomerSerializer
    permission_module = "customer"
    search_fields = ["name", "mobile", "email", "address"]
    filter_fields = ["status", "gender"]
    export_name = "customers"


class SupplierViewSet(BaseViewSet):
    queryset = m.Supplier.objects.all()
    serializer_class = s.SupplierSerializer
    permission_module = "supplier"
    search_fields = ["name", "mobile", "email", "gstin", "address"]
    filter_fields = ["status"]
    export_name = "suppliers"


class EmployeeViewSet(BaseViewSet):
    queryset = m.Employee.objects.all()
    serializer_class = s.EmployeeSerializer
    permission_module = "employee"
    search_fields = ["employee_code", "name", "mobile", "email", "designation", "department"]
    filter_fields = ["status", "department", "designation"]
    export_name = "employees"


class SizeViewSet(BaseViewSet):
    queryset = m.Size.objects.all()
    serializer_class = s.SizeSerializer
    permission_module = "size"
    search_fields = ["name"]
    filter_fields = ["status"]
    ordering = ["sort_order", "name"]
    export_name = "sizes"


class ColourViewSet(BaseViewSet):
    queryset = m.Colour.objects.all()
    serializer_class = s.ColourSerializer
    permission_module = "colour"
    search_fields = ["name", "code"]
    filter_fields = ["status"]
    export_name = "colours"


class BrandViewSet(BaseViewSet):
    queryset = m.Brand.objects.all()
    serializer_class = s.BrandSerializer
    permission_module = "brand"
    search_fields = ["name", "description"]
    filter_fields = ["status"]
    export_name = "brands"


class ProductViewSet(BaseViewSet):
    queryset = m.Product.objects.select_related("category", "unit", "brand").annotate(
        # sub-queries (not joins) so counts stay correct when the search filter joins variants
        variant_count=Coalesce(
            Subquery(m.ProductVariant.objects.filter(product=OuterRef("pk")).values("product").annotate(c=Count("id")).values("c"), output_field=IntegerField()), 0
        ),
        total_stock=Coalesce(
            Subquery(m.ProductVariant.objects.filter(product=OuterRef("pk")).values("product").annotate(c=Sum("current_stock")).values("c"), output_field=IntegerField()), 0
        ),
    )
    serializer_class = s.ProductSerializer
    permission_module = "product"
    search_fields = ["product_code", "name", "description", "category__name", "brand__name", "variants__sku", "variants__barcode"]
    filter_fields = ["status", "category", "brand", "unit"]
    export_name = "products"


class ProductVariantViewSet(BaseViewSet):
    queryset = m.ProductVariant.objects.select_related("product", "product__category", "size", "colour", "warehouse", "zone", "rack", "bin")
    serializer_class = s.ProductVariantSerializer
    permission_module = "product"
    search_fields = ["sku", "barcode", "product__name", "product__product_code", "size__name", "colour__name"]
    filter_fields = ["status", "product", "size", "colour", "warehouse", ("category", "product__category"), ("barcode", "barcode")]
    export_name = "product_variants"
    permission_actions = {"by_barcode": "VIEW"}

    def get_queryset(self):
        qs = super().get_queryset()
        stock_status = self.request.query_params.get("stock_status")
        return qs.with_status(stock_status) if stock_status else qs

    @action(detail=False, methods=["get"], url_path="by-barcode")
    def by_barcode(self, request):
        """Exact barcode (or SKU) lookup used by the POS scanner input and stock forms."""
        code = request.query_params.get("code", "").strip()
        variant = m.ProductVariant.objects.select_related("product", "size", "colour").filter(status="ACTIVE", barcode=code).first()
        if variant is None:
            variant = m.ProductVariant.objects.select_related("product", "size", "colour").filter(status="ACTIVE", sku__iexact=code).first()
        if variant is None:
            return Response({"detail": f"No active product found for barcode {code}."}, status=404)
        return Response(self.get_serializer(variant).data)
