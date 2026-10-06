from django.conf import settings
from django.db import models, transaction


class Status(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class BaseModel(models.Model):
    """created_at / updated_at / created_by on every business table."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        abstract = True


class DocumentSequence(models.Model):
    """Gap-free, race-safe counters for document numbers, invoice numbers and barcodes."""

    name = models.CharField(max_length=50, unique=True)
    last_number = models.PositiveBigIntegerField(default=0)

    def __str__(self):
        return f"{self.name}: {self.last_number}"

    @classmethod
    def next(cls, name):
        with transaction.atomic():
            cls.objects.get_or_create(name=name)
            seq = cls.objects.select_for_update().get(name=name)
            seq.last_number += 1
            seq.save(update_fields=["last_number"])
            return seq.last_number
