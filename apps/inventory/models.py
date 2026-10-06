from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class MovementType(models.TextChoices):
    STOCK_IN = "STOCK_IN", "Stock In"
    STOCK_OUT = "STOCK_OUT", "Stock Out"
    SALE = "SALE", "Sale"
    SALE_RETURN = "SALE_RETURN", "Sale Return"
    ADJUSTMENT_IN = "ADJUSTMENT_IN", "Adjustment In"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT", "Adjustment Out"


class StockMovement(models.Model):
    """Immutable audit trail: every stock change in the system writes exactly one row here."""

    variant = models.ForeignKey("masters.ProductVariant", on_delete=models.PROTECT, related_name="movements")
    warehouse = models.ForeignKey("masters.Warehouse", null=True, blank=True, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices, db_index=True)
    quantity = models.PositiveIntegerField()
    previous_stock = models.IntegerField()
    new_stock = models.IntegerField()
    reference_type = models.CharField(max_length=30, blank=True)
    reference_id = models.PositiveBigIntegerField(null=True, blank=True)
    reference_no = models.CharField(max_length=40, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "stock_movements"
        ordering = ["-id"]
        indexes = [models.Index(fields=["variant", "created_at"]), models.Index(fields=["reference_type", "reference_id"])]

    def __str__(self):
        return f"{self.movement_type} {self.quantity} x {self.variant_id}"


class StockIn(BaseModel):
    document_no = models.CharField(max_length=30, unique=True)
    date = models.DateField(default=timezone.localdate, db_index=True)
    supplier = models.ForeignKey("masters.Supplier", on_delete=models.PROTECT, related_name="stock_ins")
    warehouse = models.ForeignKey("masters.Warehouse", on_delete=models.PROTECT, related_name="stock_ins")
    zone = models.ForeignKey("masters.Zone", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    rack = models.ForeignKey("masters.Rack", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    bin = models.ForeignKey("masters.Bin", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    batch_reference = models.CharField("batch / reference", max_length=80, blank=True)
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "stock_in"
        ordering = ["-id"]

    def __str__(self):
        return self.document_no


class StockInItem(models.Model):
    stock_in = models.ForeignKey(StockIn, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("masters.ProductVariant", on_delete=models.PROTECT, related_name="stock_in_items")
    quantity = models.PositiveIntegerField()
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "stock_in_items"


class StockOut(BaseModel):
    class Reason(models.TextChoices):
        DAMAGED = "DAMAGED", "Damaged"
        EXPIRED = "EXPIRED", "Expired"
        LOST = "LOST", "Lost / Missing"
        INTERNAL_USE = "INTERNAL_USE", "Internal use"
        SUPPLIER_RETURN = "SUPPLIER_RETURN", "Return to supplier"
        OTHER = "OTHER", "Other"

    document_no = models.CharField(max_length=30, unique=True)
    date = models.DateField(default=timezone.localdate, db_index=True)
    warehouse = models.ForeignKey("masters.Warehouse", on_delete=models.PROTECT, related_name="stock_outs")
    reason = models.CharField(max_length=20, choices=Reason.choices, db_index=True)
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "stock_out"
        ordering = ["-id"]

    def __str__(self):
        return self.document_no


class StockOutItem(models.Model):
    stock_out = models.ForeignKey(StockOut, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("masters.ProductVariant", on_delete=models.PROTECT, related_name="stock_out_items")
    quantity = models.PositiveIntegerField()

    class Meta:
        db_table = "stock_out_items"


class StockAdjustment(BaseModel):
    class Type(models.TextChoices):
        INCREASE = "INCREASE", "Increase"
        DECREASE = "DECREASE", "Decrease"

    document_no = models.CharField(max_length=30, unique=True)
    date = models.DateField(default=timezone.localdate, db_index=True)
    warehouse = models.ForeignKey("masters.Warehouse", on_delete=models.PROTECT, related_name="stock_adjustments")
    adjustment_type = models.CharField(max_length=10, choices=Type.choices, db_index=True)
    reason = models.CharField(max_length=160)
    approved_by = models.CharField(max_length=120, blank=True)
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "stock_adjustments"
        ordering = ["-id"]

    def __str__(self):
        return self.document_no


class StockAdjustmentItem(models.Model):
    adjustment = models.ForeignKey(StockAdjustment, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("masters.ProductVariant", on_delete=models.PROTECT, related_name="adjustment_items")
    quantity = models.PositiveIntegerField()

    class Meta:
        db_table = "stock_adjustment_items"
