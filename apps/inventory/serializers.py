from decimal import Decimal

from rest_framework import serializers

from apps.core.serializers import make_serializer
from apps.masters.serializers import validate_location

from . import services
from .models import StockAdjustment, StockAdjustmentItem, StockIn, StockInItem, StockMovement, StockOut, StockOutItem


class ItemSerializer(serializers.ModelSerializer):
    variant_label = serializers.CharField(source="variant.__str__", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    barcode = serializers.CharField(source="variant.barcode", read_only=True)
    quantity = serializers.IntegerField(min_value=1)


def item_serializer(model, extra_fields=(), **declared):
    meta = type("Meta", (), {"model": model, "fields": ["id", "variant", "variant_label", "sku", "barcode", "quantity", *extra_fields]})
    return type(f"{model.__name__}Serializer", (ItemSerializer,), {"Meta": meta, **declared})


StockInItemSerializer = item_serializer(
    StockInItem, ["purchase_price"], purchase_price=serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
)
StockOutItemSerializer = item_serializer(StockOutItem)
StockAdjustmentItemSerializer = item_serializer(StockAdjustmentItem)


class DocumentSerializer(serializers.ModelSerializer):
    """Header + line items written together; the service layer does the atomic stock update."""

    service = None

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Add at least one product line.")
        return items

    def create(self, validated_data):
        items = validated_data.pop("items")
        validated_data.pop("created_by", None)  # the service stamps the user itself
        return type(self).service(self.context["request"].user, validated_data, items)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["total_quantity"] = sum(i["quantity"] for i in data["items"])
        return data


def document_serializer(model, items_serializer, service, extra_validate=None):
    attrs = {f"{f.name}_name": serializers.StringRelatedField(source=f.name, read_only=True) for f in model._meta.fields if f.is_relation and f.name != "created_by"}
    meta = type("Meta", (), {"model": model, "fields": "__all__", "read_only_fields": ["document_no", "created_by", "created_at", "updated_at"]})
    attrs.update({"Meta": meta, "items": items_serializer(many=True), "service": staticmethod(service)})
    if extra_validate:
        attrs["validate"] = extra_validate
    return type(f"{model.__name__}Serializer", (DocumentSerializer,), attrs)


def _validate_stock_in(self, attrs):
    validate_location(attrs)
    return attrs


StockInSerializer = document_serializer(StockIn, StockInItemSerializer, services.create_stock_in, _validate_stock_in)
StockOutSerializer = document_serializer(StockOut, StockOutItemSerializer, services.create_stock_out)
StockAdjustmentSerializer = document_serializer(StockAdjustment, StockAdjustmentItemSerializer, services.create_adjustment)

StockMovementSerializer = make_serializer(
    StockMovement,
    extra={
        "sku": serializers.CharField(source="variant.sku", read_only=True),
        "created_by_name": serializers.StringRelatedField(source="created_by", read_only=True),
    },
)
