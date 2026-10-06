from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel


class Sale(BaseModel):
    class Status(models.TextChoices):
        COMPLETED = "COMPLETED", "Completed"
        PARTIAL_RETURN = "PARTIAL_RETURN", "Partially returned"
        RETURNED = "RETURNED", "Fully returned"

    invoice_no = models.CharField(max_length=30, unique=True)
    date = models.DateTimeField(default=timezone.now, db_index=True)
    customer = models.ForeignKey("masters.Customer", null=True, blank=True, on_delete=models.PROTECT, related_name="sales")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED, db_index=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "sales"
        ordering = ["-id"]

    def __str__(self):
        return self.invoice_no


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("masters.ProductVariant", on_delete=models.PROTECT, related_name="sale_items")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Purchase cost snapshot at the time of sale")
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, help_text="quantity x unit_price - discount (before tax)")

    class Meta:
        db_table = "sale_items"


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        UPI = "UPI", "UPI"
        CARD = "CARD", "Card"

    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=10, choices=Method.choices, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payments"


class SalesReturn(BaseModel):
    class Status(models.TextChoices):
        COMPLETED = "COMPLETED", "Completed"

    return_no = models.CharField(max_length=30, unique=True)
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="returns")
    date = models.DateField(default=timezone.localdate, db_index=True)
    customer = models.ForeignKey("masters.Customer", null=True, blank=True, on_delete=models.PROTECT, related_name="sales_returns")
    reason = models.CharField(max_length=160)
    refund_method = models.CharField(max_length=10, choices=Payment.Method.choices)
    refund_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "sales_returns"
        ordering = ["-id"]

    def __str__(self):
        return self.return_no


class SalesReturnItem(models.Model):
    sales_return = models.ForeignKey(SalesReturn, on_delete=models.CASCADE, related_name="items")
    sale_item = models.ForeignKey(SaleItem, on_delete=models.PROTECT, related_name="return_items")
    variant = models.ForeignKey("masters.ProductVariant", on_delete=models.PROTECT, related_name="return_items")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, help_text="Net selling price per unit after discount, before tax")
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Net value returned (before tax)")

    class Meta:
        db_table = "sales_return_items"
