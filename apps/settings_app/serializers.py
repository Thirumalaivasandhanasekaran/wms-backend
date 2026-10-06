from rest_framework import serializers

from .models import BusinessSettings, HardwareSettings, InvoiceSettings, PaymentSettings


def make(model):
    meta = type("Meta", (), {"model": model, "fields": "__all__", "read_only_fields": ["id", "updated_at"]})
    return type(f"{model.__name__}Serializer", (serializers.ModelSerializer,), {"Meta": meta})


BusinessSerializer = make(BusinessSettings)
InvoiceSerializer = make(InvoiceSettings)
PaymentSerializer = make(PaymentSettings)
HardwareSerializer = make(HardwareSettings)
