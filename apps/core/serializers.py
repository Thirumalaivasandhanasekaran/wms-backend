from rest_framework import serializers


def make_serializer(model, extra=None, read_only=()):
    """Build a ModelSerializer exposing every field plus a `<fk>_name` display value for each relation."""
    attrs = {}
    for field in model._meta.fields:
        if field.is_relation and field.name != "created_by":
            attrs[f"{field.name}_name"] = serializers.StringRelatedField(source=field.name, read_only=True)
    meta = type(
        "Meta",
        (),
        {
            "model": model,
            "fields": "__all__",
            "read_only_fields": ["created_by", "created_at", "updated_at", *read_only],
        },
    )
    attrs["Meta"] = meta
    attrs.update(extra or {})
    return type(f"{model.__name__}Serializer", (serializers.ModelSerializer,), attrs)
