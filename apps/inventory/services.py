"""All stock changes go through apply_movement(): one place that updates stock, refuses negative
stock and writes the audit row. Callers must run inside transaction.atomic (the public functions do)."""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.models import DocumentSequence
from apps.masters.models import ProductVariant

from .models import MovementType, StockAdjustment, StockAdjustmentItem, StockIn, StockInItem, StockMovement, StockOut, StockOutItem


def doc_no(prefix, sequence):
    return f"{prefix}{DocumentSequence.next(sequence):06d}"


def lock_variants(variant_ids):
    """Row-lock variants in id order (prevents deadlocks and lost updates under concurrent sales)."""
    ids = sorted(set(variant_ids))
    locked = {v.id: v for v in ProductVariant.objects.select_for_update().filter(id__in=ids).order_by("id")}
    if len(locked) != len(ids):
        raise ValidationError({"detail": "One or more products no longer exist."})
    return locked


def apply_movement(variant, delta, movement_type, user, warehouse=None, ref_type="", ref_id=None, ref_no=""):
    """`variant` must be a locked instance from lock_variants()."""
    new_stock = variant.current_stock + delta
    if new_stock < 0:
        raise ValidationError(
            {"detail": f"Insufficient stock for {variant.sku} ({variant}). Available: {variant.current_stock}, requested: {abs(delta)}."}
        )
    previous = variant.current_stock
    variant.current_stock = new_stock
    variant.save(update_fields=["current_stock", "updated_at"])
    return StockMovement.objects.create(
        variant=variant, warehouse=warehouse or variant.warehouse, movement_type=movement_type, quantity=abs(delta),
        previous_stock=previous, new_stock=new_stock, reference_type=ref_type, reference_id=ref_id, reference_no=ref_no, created_by=user,
    )


@transaction.atomic
def record_opening_stock(variant, user):
    locked = lock_variants([variant.id])[variant.id]
    apply_movement(locked, locked.opening_stock, MovementType.ADJUSTMENT_IN, user, ref_type="OPENING", ref_id=variant.id, ref_no="OPENING")
    variant.current_stock = locked.current_stock


@transaction.atomic
def create_stock_in(user, header, items):
    document = StockIn.objects.create(document_no=doc_no("SI-", "STOCK_IN"), created_by=user, **header)
    locked = lock_variants([i["variant"].id for i in items])
    for item in items:
        variant = locked[item["variant"].id]
        StockInItem.objects.create(stock_in=document, variant=variant, quantity=item["quantity"], purchase_price=item["purchase_price"])
        apply_movement(variant, item["quantity"], MovementType.STOCK_IN, user, header["warehouse"], "STOCK_IN", document.id, document.document_no)
        # keep the latest purchase cost on the variant: profit reports snapshot it at sale time
        variant.purchase_price = item["purchase_price"]
        variant.save(update_fields=["purchase_price"])
    return document


@transaction.atomic
def create_stock_out(user, header, items):
    document = StockOut.objects.create(document_no=doc_no("SO-", "STOCK_OUT"), created_by=user, **header)
    locked = lock_variants([i["variant"].id for i in items])
    for item in items:
        variant = locked[item["variant"].id]
        StockOutItem.objects.create(stock_out=document, variant=variant, quantity=item["quantity"])
        apply_movement(variant, -item["quantity"], MovementType.STOCK_OUT, user, header["warehouse"], "STOCK_OUT", document.id, document.document_no)
    return document


@transaction.atomic
def create_adjustment(user, header, items):
    document = StockAdjustment.objects.create(document_no=doc_no("ADJ-", "STOCK_ADJ"), created_by=user, **header)
    increase = header["adjustment_type"] == StockAdjustment.Type.INCREASE
    locked = lock_variants([i["variant"].id for i in items])
    for item in items:
        variant = locked[item["variant"].id]
        StockAdjustmentItem.objects.create(adjustment=document, variant=variant, quantity=item["quantity"])
        apply_movement(
            variant, item["quantity"] if increase else -item["quantity"],
            MovementType.ADJUSTMENT_IN if increase else MovementType.ADJUSTMENT_OUT,
            user, header["warehouse"], "STOCK_ADJUSTMENT", document.id, document.document_no,
        )
    return document
