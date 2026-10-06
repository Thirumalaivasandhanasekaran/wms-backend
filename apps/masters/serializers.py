from django.db import transaction
from rest_framework import serializers

from apps.core.serializers import make_serializer

from . import models as m
from .services import build_sku, next_barcode


def validate_location(attrs, instance=None):
    """Zone must belong to the warehouse, rack to the zone, bin to the rack."""

    def get(name):
        return attrs.get(name, getattr(instance, name, None) if instance else None)

    warehouse, zone, rack, bin_ = get("warehouse"), get("zone"), get("rack"), get("bin")
    if zone and warehouse and zone.warehouse_id != warehouse.id:
        raise serializers.ValidationError({"zone": "This zone does not belong to the selected warehouse."})
    if rack and zone and rack.zone_id != zone.id:
        raise serializers.ValidationError({"rack": "This rack does not belong to the selected zone."})
    if bin_ and rack and bin_.rack_id != rack.id:
        raise serializers.ValidationError({"bin": "This bin does not belong to the selected rack."})


WarehouseSerializer = make_serializer(m.Warehouse)
UnitSerializer = make_serializer(m.Unit)
CategorySerializer = make_serializer(m.Category)
MaterialSerializer = make_serializer(m.Material)
CustomerSerializer = make_serializer(m.Customer)
SupplierSerializer = make_serializer(m.Supplier)
EmployeeSerializer = make_serializer(m.Employee)
SizeSerializer = make_serializer(m.Size)
ColourSerializer = make_serializer(m.Colour)
BrandSerializer = make_serializer(m.Brand)

_ZoneBase = make_serializer(m.Zone)
_RackBase = make_serializer(m.Rack)
_BinBase = make_serializer(m.Bin)


class ZoneSerializer(_ZoneBase):
    pass


class RackSerializer(_RackBase):
    def validate(self, attrs):
        validate_location(attrs, self.instance)
        return attrs


class BinSerializer(_BinBase):
    def validate(self, attrs):
        validate_location(attrs, self.instance)
        return attrs


_ProductBase = make_serializer(
    m.Product,
    extra={
        "variant_count": serializers.IntegerField(read_only=True),
        "total_stock": serializers.IntegerField(read_only=True),
    },
)


class ProductSerializer(_ProductBase):
    pass


_VariantBase = make_serializer(
    m.ProductVariant,
    extra={
        "label": serializers.CharField(source="__str__", read_only=True),
        "stock_status": serializers.CharField(source="status_code", read_only=True),
        "category_name": serializers.StringRelatedField(source="product.category", read_only=True),
        "sku": serializers.CharField(required=False, allow_blank=True, max_length=60),
        "barcode": serializers.CharField(required=False, allow_blank=True, max_length=60),
        "minimum_stock": serializers.IntegerField(required=False, min_value=0),
    },
    read_only=["current_stock"],
)


class ProductVariantSerializer(_VariantBase):
    """Product + Variant architecture: size/colour/barcode/price/stock live on the variant."""

    class Meta(_VariantBase.Meta):
        # unique_together validators are replaced by the checks below so SKU/barcode can be auto-generated
        validators = []

    def validate(self, attrs):
        validate_location(attrs, self.instance)
        inst = self.instance
        product = attrs.get("product", inst.product if inst else None)
        size = attrs.get("size", inst.size if inst else None)
        colour = attrs.get("colour", inst.colour if inst else None)
        dupe = m.ProductVariant.objects.filter(product=product, size=size, colour=colour)
        if inst:
            dupe = dupe.exclude(pk=inst.pk)
        if dupe.exists():
            raise serializers.ValidationError("This product already has a variant with the same size and colour.")
        return attrs

    def validate_sku(self, value):
        return value.strip().upper()

    def validate_barcode(self, value):
        return value.strip()

    @transaction.atomic
    def create(self, validated_data):
        from apps.inventory.services import record_opening_stock

        product = validated_data["product"]
        if not validated_data.get("sku"):
            validated_data["sku"] = build_sku(product, validated_data.get("size"), validated_data.get("colour"))
        if not validated_data.get("barcode"):
            validated_data["barcode"] = next_barcode()
        if "minimum_stock" not in validated_data:
            validated_data["minimum_stock"] = product.minimum_stock
        for field, label in (("sku", "SKU"), ("barcode", "Barcode")):
            if m.ProductVariant.objects.filter(**{field: validated_data[field]}).exists():
                raise serializers.ValidationError({field: f"This {label} is already used by another variant."})
        variant = super().create(validated_data)
        if variant.opening_stock:
            record_opening_stock(variant, self.context["request"].user)
        return variant

    def update(self, instance, validated_data):
        validated_data.pop("opening_stock", None)  # opening stock is fixed after creation; use Stock In / Adjustment
        for field, label in (("sku", "SKU"), ("barcode", "Barcode")):
            if validated_data.get(field) and m.ProductVariant.objects.filter(**{field: validated_data[field]}).exclude(pk=instance.pk).exists():
                raise serializers.ValidationError({field: f"This {label} is already used by another variant."})
        return super().update(instance, {k: v for k, v in validated_data.items() if v != "" or k not in ("sku", "barcode")})
