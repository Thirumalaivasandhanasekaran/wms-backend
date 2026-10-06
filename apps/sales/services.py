from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from apps.core.models import DocumentSequence
from apps.inventory.models import MovementType
from apps.inventory.services import apply_movement, doc_no, lock_variants
from apps.settings_app.models import InvoiceSettings, PaymentSettings

from .models import Payment, Sale, SaleItem, SalesReturn, SalesReturnItem

CENT = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


@transaction.atomic
def complete_sale(user, customer, items, payments, notes=""):
    """Validate -> sale -> items -> payment -> stock reduction -> movements -> invoice number, all or nothing."""
    if not items:
        raise ValidationError({"detail": "The cart is empty."})
    invoice = InvoiceSettings.load()
    pay_settings = PaymentSettings.load()
    locked = lock_variants([i["variant"].id for i in items])

    subtotal = discount_total = Decimal("0")
    lines = []
    for item in items:
        variant = locked[item["variant"].id]
        qty = item["quantity"]
        if variant.status != "ACTIVE":
            raise ValidationError({"detail": f"{variant.sku} is inactive and cannot be sold."})
        gross = money(variant.selling_price * qty)  # price always comes from the server, never the browser
        discount = money(item.get("discount") or 0)
        if discount < 0 or discount > gross:
            raise ValidationError({"detail": f"Invalid discount for {variant.sku}."})
        lines.append((variant, qty, gross, discount))
        subtotal += gross
        discount_total += discount

    taxable = subtotal - discount_total
    tax_total = money(taxable * invoice.tax_percent / 100)
    grand_total = taxable + tax_total

    allowed = {"CASH": pay_settings.cash_enabled, "UPI": pay_settings.upi_enabled, "CARD": pay_settings.card_enabled}
    paid = Decimal("0")
    for p in payments:
        if not allowed.get(p["method"], False):
            raise ValidationError({"detail": f"{p['method']} payments are disabled in Payment Settings."})
        paid += money(p["amount"])
    if paid != grand_total:
        raise ValidationError({"detail": f"Payment total {paid} does not match the grand total {grand_total}."})

    sale = Sale.objects.create(
        invoice_no=doc_no(invoice.invoice_prefix, "INVOICE"), customer=customer, subtotal=subtotal,
        discount_total=discount_total, tax_total=tax_total, grand_total=grand_total, notes=notes, created_by=user,
    )
    for variant, qty, gross, discount in lines:
        SaleItem.objects.create(
            sale=sale, variant=variant, quantity=qty, unit_price=variant.selling_price,
            cost_price=variant.purchase_price, discount=discount, line_total=gross - discount,
        )
        apply_movement(variant, -qty, MovementType.SALE, user, ref_type="SALE", ref_id=sale.id, ref_no=sale.invoice_no)
    Payment.objects.bulk_create([Payment(sale=sale, method=p["method"], amount=money(p["amount"]), reference=p.get("reference", "")) for p in payments])
    return sale


@transaction.atomic
def create_sales_return(user, sale_id, header, items):
    sale = Sale.objects.select_for_update().get(pk=sale_id)  # serialises concurrent returns of one invoice
    sale_items = {si.id: si for si in sale.items.select_related("variant")}
    taxable = sale.subtotal - sale.discount_total
    tax_rate = (sale.tax_total / taxable) if taxable else Decimal("0")

    prepared = []
    for item in items:
        si = sale_items.get(item["sale_item"].id)
        if si is None:
            raise ValidationError({"detail": "A returned line does not belong to this invoice."})
        already = si.return_items.aggregate(q=Sum("quantity"))["q"] or 0
        if item["quantity"] + already > si.quantity:
            raise ValidationError({"detail": f"{si.variant.sku}: cannot return {item['quantity']}; sold {si.quantity}, already returned {already}."})
        net_unit = money(si.line_total / si.quantity)
        prepared.append((si, item["quantity"], net_unit))

    locked = lock_variants([si.variant_id for si, _, _ in prepared])
    refund_net = sum((money(net_unit * qty) for _, qty, net_unit in prepared), Decimal("0"))
    document = SalesReturn.objects.create(
        return_no=doc_no("SR-", "SALE_RETURN"), sale=sale, customer=sale.customer, refund_total=money(refund_net * (1 + tax_rate)),
        created_by=user, **header,
    )
    for si, qty, net_unit in prepared:
        SalesReturnItem.objects.create(
            sales_return=document, sale_item=si, variant=si.variant, quantity=qty, unit_price=net_unit,
            cost_price=si.cost_price, amount=money(net_unit * qty),
        )
        apply_movement(locked[si.variant_id], qty, MovementType.SALE_RETURN, user, ref_type="SALES_RETURN", ref_id=document.id, ref_no=document.return_no)

    sold = sum(si.quantity for si in sale_items.values())
    returned = SalesReturnItem.objects.filter(sales_return__sale=sale).aggregate(q=Sum("quantity"))["q"] or 0
    sale.status = Sale.Status.RETURNED if returned >= sold else Sale.Status.PARTIAL_RETURN
    sale.save(update_fields=["status", "updated_at"])
    return document
