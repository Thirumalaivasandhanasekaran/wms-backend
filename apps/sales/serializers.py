from django.db.models import Sum
from rest_framework import serializers

from apps.masters.models import ProductVariant

from . import services
from .models import Payment, Sale, SaleItem, SalesReturn, SalesReturnItem


class SaleItemSerializer(serializers.ModelSerializer):
    variant_label = serializers.CharField(source="variant.__str__", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    size_name = serializers.StringRelatedField(source="variant.size", read_only=True)
    colour_name = serializers.StringRelatedField(source="variant.colour", read_only=True)
    returned_quantity = serializers.SerializerMethodField()
    # write-only inputs for POS (price is never accepted from the client)
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False, default=0)

    class Meta:
        model = SaleItem
        fields = ["id", "variant", "variant_label", "sku", "size_name", "colour_name", "quantity", "unit_price", "discount", "line_total", "returned_quantity"]
        read_only_fields = ["unit_price", "line_total"]

    def get_returned_quantity(self, obj):
        return obj.return_items.aggregate(q=Sum("quantity"))["q"] or 0


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "method", "amount", "reference"]


class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    payments = PaymentSerializer(many=True)
    customer_name = serializers.StringRelatedField(source="customer", read_only=True)
    cashier = serializers.StringRelatedField(source="created_by", read_only=True)
    payment_method = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ["id", "invoice_no", "date", "customer", "customer_name", "subtotal", "discount_total", "tax_total", "grand_total", "status", "notes", "cashier", "payment_method", "items", "payments"]
        read_only_fields = ["invoice_no", "date", "subtotal", "discount_total", "tax_total", "grand_total", "status"]

    def get_payment_method(self, obj):
        return ", ".join(p.method for p in obj.payments.all())

    def validate(self, attrs):
        if not attrs.get("items"):
            raise serializers.ValidationError({"detail": "The cart is empty."})
        if not attrs.get("payments"):
            raise serializers.ValidationError({"detail": "Select a payment method."})
        return attrs

    def create(self, validated_data):
        return services.complete_sale(
            self.context["request"].user, validated_data.get("customer"),
            validated_data["items"], validated_data["payments"], validated_data.get("notes", ""),
        )


class SalesReturnItemSerializer(serializers.ModelSerializer):
    variant_label = serializers.CharField(source="variant.__str__", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = SalesReturnItem
        fields = ["id", "sale_item", "variant", "variant_label", "sku", "quantity", "unit_price", "amount"]
        read_only_fields = ["variant", "unit_price", "amount"]


class SalesReturnSerializer(serializers.ModelSerializer):
    items = SalesReturnItemSerializer(many=True)
    invoice_no = serializers.CharField(source="sale.invoice_no", read_only=True)
    customer_name = serializers.StringRelatedField(source="customer", read_only=True)

    class Meta:
        model = SalesReturn
        fields = ["id", "return_no", "sale", "invoice_no", "date", "customer", "customer_name", "reason", "refund_method", "refund_total", "status", "remarks", "items", "created_at"]
        read_only_fields = ["return_no", "customer", "refund_total", "status", "created_at"]

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Select at least one item to return.")
        return items

    def create(self, validated_data):
        items = validated_data.pop("items")
        sale = validated_data.pop("sale")
        validated_data.pop("created_by", None)
        return services.create_sales_return(self.context["request"].user, sale.id, validated_data, items)
