from django.db import models


class SingletonModel(models.Model):
    """One configuration row per table (pk is always 1)."""

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class BusinessSettings(SingletonModel):
    shop_name = models.CharField(max_length=160, default="My Shop")
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    gstin = models.CharField("GSTIN", max_length=20, blank=True)
    logo = models.ImageField(upload_to="business/", null=True, blank=True)

    class Meta:
        db_table = "business_settings"


class InvoiceSettings(SingletonModel):
    class Paper(models.TextChoices):
        THERMAL_80 = "THERMAL_80", "Thermal 80 mm"
        THERMAL_58 = "THERMAL_58", "Thermal 58 mm"
        A4 = "A4", "A4"

    invoice_prefix = models.CharField(max_length=10, default="INV-")
    receipt_title = models.CharField(max_length=80, default="TAX INVOICE")
    footer = models.CharField(max_length=255, default="Thank you! Visit again.", blank=True)
    paper_format = models.CharField(max_length=12, choices=Paper.choices, default=Paper.THERMAL_80)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="GST % added on top of item prices")

    class Meta:
        db_table = "invoice_settings"


class PaymentSettings(SingletonModel):
    cash_enabled = models.BooleanField(default=True)
    upi_enabled = models.BooleanField(default=True)
    upi_id = models.CharField(max_length=80, blank=True)
    card_enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "payment_settings"


class HardwareSettings(SingletonModel):
    barcode_scanner_enabled = models.BooleanField(default=True)
    scanner_autofocus = models.BooleanField(default=True, help_text="Keep the POS barcode box focused for the scanner")
    thermal_printer_enabled = models.BooleanField(default=False)
    thermal_paper_width = models.PositiveSmallIntegerField(default=80, choices=[(58, "58 mm"), (80, "80 mm")])
    auto_print_receipt = models.BooleanField(default=False)
    label_printer_enabled = models.BooleanField(default=False)
    label_width_mm = models.PositiveSmallIntegerField(default=50)
    label_height_mm = models.PositiveSmallIntegerField(default=25)
    cash_drawer_enabled = models.BooleanField(default=False, help_text="Drawer wired to the receipt printer (opens on print)")
    customer_display_enabled = models.BooleanField(default=False)

    class Meta:
        db_table = "hardware_settings"
