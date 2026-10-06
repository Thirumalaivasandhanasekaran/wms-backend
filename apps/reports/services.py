"""Report queries. Every report returns (rows, columns, summary); rows are DB-side `values()` querysets
(or small aggregated lists) so pagination happens in PostgreSQL."""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from apps.inventory.models import StockAdjustmentItem, StockInItem, StockMovement, StockOutItem
from apps.masters.models import ProductVariant
from apps.sales.models import Payment, Sale, SaleItem, SalesReturnItem

MONEY = DecimalField(max_digits=14, decimal_places=2)


def col(key, label, kind="text"):
    return {"key": key, "label": label, "type": kind}


def apply(qs, params, mapping):
    """mapping: {query_param: orm_lookup}. Empty params are ignored."""
    for param, lookup in mapping.items():
        value = params.get(param)
        if value not in (None, ""):
            qs = qs.filter(**{lookup: value})
    return qs


def dates(qs, params, field, datetime_field=False):
    suffix = "__date" if datetime_field else ""
    return apply(qs, params, {"date_from": f"{field}{suffix}__gte", "date_to": f"{field}{suffix}__lte"})


def variant_rows(qs):
    return qs.annotate_status().values(
        "id", "sku", "barcode", "minimum_stock", "stock_status", product_name=F("product__name"), category_name=F("product__category__name"),
        size_name=F("size__name"), colour_name=F("colour__name"), warehouse_name=F("warehouse__name"), stock=F("current_stock"),
    ).order_by("product__name", "sku")


def current_stock(params):
    qs = ProductVariant.objects.all()
    qs = apply(qs, params, {"category": "product__category", "product": "product", "size": "size", "colour": "colour", "barcode": "barcode__icontains", "warehouse": "warehouse"})
    if params.get("status"):
        qs = qs.with_status(params["status"])
    rows = variant_rows(qs)
    cols = [col("product_name", "Product"), col("sku", "Variant (SKU)"), col("size_name", "Size"), col("colour_name", "Colour"), col("barcode", "Barcode"),
            col("warehouse_name", "Warehouse"), col("stock", "Stock", "number"), col("minimum_stock", "Minimum Stock", "number"), col("stock_status", "Status", "stock")]
    return rows, cols, None


def low_stock(params):
    qs = apply(ProductVariant.objects.low_stock(), params, {"category": "product__category"})
    rows = variant_rows(qs)
    cols = [col("product_name", "Product"), col("sku", "Variant (SKU)"), col("size_name", "Size"), col("colour_name", "Colour"),
            col("stock", "Current Stock", "number"), col("minimum_stock", "Minimum Stock", "number"), col("stock_status", "Status", "stock")]
    return rows, cols, None


def out_of_stock(params):
    qs = ProductVariant.objects.out_of_stock()
    qs = apply(qs, params, {"category": "product__category"})
    rows = variant_rows(qs)
    cols = [col("product_name", "Product"), col("sku", "Variant (SKU)"), col("size_name", "Size"), col("colour_name", "Colour"), col("barcode", "Barcode"), col("category_name", "Category")]
    return rows, cols, None


def stock_in(params):
    qs = StockInItem.objects.all()
    qs = dates(qs, params, "stock_in__date")
    qs = apply(qs, params, {"supplier": "stock_in__supplier", "product": "variant__product", "variant": "variant", "warehouse": "stock_in__warehouse", "document_no": "stock_in__document_no__icontains"})
    rows = qs.values(
        "id", document_no=F("stock_in__document_no"), date=F("stock_in__date"), supplier_name=F("stock_in__supplier__name"), warehouse_name=F("stock_in__warehouse__name"),
        product=F("variant__product__name"), sku=F("variant__sku"), batch=F("stock_in__batch_reference"), qty=F("quantity"), price=F("purchase_price"),
        total=ExpressionWrapper(F("quantity") * F("purchase_price"), output_field=MONEY),
    ).order_by("-stock_in__date", "-id")
    cols = [col("document_no", "Document No"), col("date", "Date", "date"), col("supplier_name", "Supplier"), col("warehouse_name", "Warehouse"), col("product", "Product"),
            col("sku", "Variant (SKU)"), col("batch", "Batch / Ref"), col("qty", "Qty", "number"), col("price", "Purchase Price", "money"), col("total", "Total", "money")]
    return rows, cols, None


def stock_out(params):
    qs = StockOutItem.objects.all()
    qs = dates(qs, params, "stock_out__date")
    qs = apply(qs, params, {"product": "variant__product", "variant": "variant", "reason": "stock_out__reason", "warehouse": "stock_out__warehouse"})
    rows = qs.values(
        "id", document_no=F("stock_out__document_no"), date=F("stock_out__date"), warehouse_name=F("stock_out__warehouse__name"), product=F("variant__product__name"),
        sku=F("variant__sku"), reason=F("stock_out__reason"), qty=F("quantity"), remarks=F("stock_out__remarks"),
    ).order_by("-stock_out__date", "-id")
    cols = [col("document_no", "Document No"), col("date", "Date", "date"), col("warehouse_name", "Warehouse"), col("product", "Product"), col("sku", "Variant (SKU)"),
            col("reason", "Reason"), col("qty", "Qty", "number"), col("remarks", "Remarks")]
    return rows, cols, None


def stock_adjustment(params):
    qs = StockAdjustmentItem.objects.all()
    qs = dates(qs, params, "adjustment__date")
    qs = apply(qs, params, {"product": "variant__product", "variant": "variant", "adjustment_type": "adjustment__adjustment_type", "reason": "adjustment__reason__icontains"})
    rows = qs.values(
        "id", document_no=F("adjustment__document_no"), date=F("adjustment__date"), warehouse_name=F("adjustment__warehouse__name"), product=F("variant__product__name"),
        sku=F("variant__sku"), adjustment_type=F("adjustment__adjustment_type"), qty=F("quantity"), reason=F("adjustment__reason"), approved_by=F("adjustment__approved_by"),
    ).order_by("-adjustment__date", "-id")
    cols = [col("document_no", "Document No"), col("date", "Date", "date"), col("warehouse_name", "Warehouse"), col("product", "Product"), col("sku", "Variant (SKU)"),
            col("adjustment_type", "Type"), col("qty", "Qty", "number"), col("reason", "Reason"), col("approved_by", "Approved By")]
    return rows, cols, None


def sales(params):
    qs = Sale.objects.all()
    qs = dates(qs, params, "date", datetime_field=True)
    qs = apply(qs, params, {"invoice": "invoice_no__icontains", "customer": "customer"})
    for param, lookup in (("product", "variant__product"), ("variant", "variant")):
        if params.get(param):
            qs = qs.filter(id__in=SaleItem.objects.filter(**{lookup: params[param]}).values("sale_id"))
    if params.get("payment_method"):
        qs = qs.filter(id__in=Payment.objects.filter(method=params["payment_method"]).values("sale_id"))
    first_payment = Payment.objects.filter(sale=OuterRef("pk")).order_by("id").values("method")[:1]
    rows = qs.annotate(payment=Subquery(first_payment)).values(
        "id", "invoice_no", "date", "subtotal", "discount_total", "tax_total", "grand_total", "payment", "status", customer_name=F("customer__name"),
    ).order_by("-date", "-id")
    cols = [col("invoice_no", "Invoice"), col("date", "Date", "datetime"), col("customer_name", "Customer"), col("subtotal", "Subtotal", "money"), col("discount_total", "Discount", "money"),
            col("tax_total", "Tax", "money"), col("grand_total", "Grand Total", "money"), col("payment", "Payment"), col("status", "Status")]
    summary = qs.aggregate(invoices=Count("id"), revenue=Coalesce(Sum("grand_total"), Decimal("0")))
    return rows, cols, summary


def sales_return(params):
    qs = SalesReturnItem.objects.all()
    qs = dates(qs, params, "sales_return__date")
    qs = apply(qs, params, {"invoice": "sales_return__sale__invoice_no__icontains", "product": "variant__product", "reason": "sales_return__reason__icontains"})
    rows = qs.values(
        "id", return_no=F("sales_return__return_no"), invoice_no=F("sales_return__sale__invoice_no"), date=F("sales_return__date"), product=F("variant__product__name"),
        sku=F("variant__sku"), qty=F("quantity"), value=F("amount"), reason=F("sales_return__reason"), refund_method=F("sales_return__refund_method"),
    ).order_by("-sales_return__date", "-id")
    cols = [col("return_no", "Return No"), col("invoice_no", "Invoice"), col("date", "Date", "date"), col("product", "Product"), col("sku", "Variant (SKU)"),
            col("qty", "Qty", "number"), col("value", "Value (ex-tax)", "money"), col("reason", "Reason"), col("refund_method", "Refund Method")]
    return rows, cols, None


def product_sales(params):
    qs = dates(SaleItem.objects.all(), params, "sale__date", datetime_field=True)
    qs = apply(qs, params, {"product": "variant__product", "variant": "variant"})
    rows = qs.values("variant", product=F("variant__product__name"), sku=F("variant__sku"), size_name=F("variant__size__name"), colour_name=F("variant__colour__name")).annotate(
        qty_sold=Sum("quantity"), revenue=Sum("line_total")
    ).order_by("-qty_sold", "product")
    cols = [col("product", "Product"), col("sku", "Variant (SKU)"), col("size_name", "Size"), col("colour_name", "Colour"), col("qty_sold", "Quantity Sold", "number"), col("revenue", "Revenue", "money")]
    return rows, cols, None


def profit_by_day(params):
    """Sales value, cost and gross profit per day, net of returns (a return reverses its own sale value and cost)."""
    cost_expr = ExpressionWrapper(F("cost_price") * F("quantity"), output_field=MONEY)
    sold = dates(SaleItem.objects.all(), params, "sale__date", datetime_field=True)
    returned = dates(SalesReturnItem.objects.all(), params, "sales_return__date")
    days = {}
    for r in sold.annotate(d=TruncDate("sale__date")).values("d").annotate(v=Sum("line_total"), c=Sum(cost_expr)):
        days.setdefault(r["d"], {})["sold"] = (r["v"] or Decimal("0"), r["c"] or Decimal("0"))
    for r in returned.values("sales_return__date").annotate(v=Sum("amount"), c=Sum(cost_expr)):
        days.setdefault(r["sales_return__date"], {})["ret"] = (r["v"] or Decimal("0"), r["c"] or Decimal("0"))
    rows = []
    for day in sorted(days, reverse=True):
        sv, sc = days[day].get("sold", (Decimal("0"), Decimal("0")))
        rv, rc = days[day].get("ret", (Decimal("0"), Decimal("0")))
        rows.append({"date": day, "sales_value": sv, "returns_value": rv, "net_sales": sv - rv, "cost_value": sc - rc, "gross_profit": (sv - rv) - (sc - rc)})
    return rows


def profit(params):
    rows = profit_by_day(params)
    cols = [col("date", "Date", "date"), col("sales_value", "Sales Value", "money"), col("returns_value", "Returns", "money"), col("net_sales", "Net Sales", "money"),
            col("cost_value", "Cost Value", "money"), col("gross_profit", "Gross Profit", "money")]
    summary = {k: sum((r[k] for r in rows), Decimal("0")) for k in ("sales_value", "returns_value", "net_sales", "cost_value", "gross_profit")}
    return rows, cols, summary


def payments(params):
    qs = dates(Payment.objects.all(), params, "sale__date", datetime_field=True)
    qs = apply(qs, params, {"payment_method": "method"})
    rows = qs.values("method").annotate(total=Sum("amount"), invoice_count=Count("sale", distinct=True)).order_by("-total")
    cols = [col("method", "Payment Method"), col("total", "Amount", "money"), col("invoice_count", "Invoice Count", "number")]
    return rows, cols, None


REPORTS = {
    "current-stock": current_stock, "stock-in": stock_in, "stock-out": stock_out, "stock-adjustment": stock_adjustment, "sales": sales,
    "sales-return": sales_return, "low-stock": low_stock, "out-of-stock": out_of_stock, "product-sales": product_sales, "profit": profit, "payments": payments,
}


def dashboard():
    today = timezone.localdate()
    variants = ProductVariant.objects.filter(status="ACTIVE")
    todays_sales = Sale.objects.filter(date__date=today)
    sale_totals = todays_sales.aggregate(orders=Count("id"), revenue=Coalesce(Sum("grand_total"), Decimal("0")), discount=Coalesce(Sum("discount_total"), Decimal("0")))
    day = {r["date"]: r for r in profit_by_day({"date_from": today.isoformat(), "date_to": today.isoformat()})}.get(today)
    since = timezone.now() - timedelta(days=30)
    top = (
        SaleItem.objects.filter(sale__date__gte=since)
        .values("variant", product=F("variant__product__name"), sku=F("variant__sku"))
        .annotate(qty_sold=Sum("quantity"), revenue=Sum("line_total")).order_by("-qty_sold")[:5]
    )
    recent = Sale.objects.order_by("-id")[:5].values("id", "invoice_no", "date", "grand_total", "status", customer_name=F("customer__name"))
    return {
        "cards": {
            "total_current_stock": variants.aggregate(t=Coalesce(Sum("current_stock"), 0))["t"],
            "low_stock": variants.low_stock().count(),
            "out_of_stock": variants.out_of_stock().count(),
            "todays_stock_in": StockInItem.objects.filter(stock_in__date=today).aggregate(t=Coalesce(Sum("quantity"), 0))["t"],
            "todays_stock_out": StockOutItem.objects.filter(stock_out__date=today).aggregate(t=Coalesce(Sum("quantity"), 0))["t"],
            "todays_sales": SaleItem.objects.filter(sale__date__date=today).aggregate(t=Coalesce(Sum("quantity"), 0))["t"],
            "todays_orders": sale_totals["orders"],
            "todays_revenue": sale_totals["revenue"],
            "todays_discount": sale_totals["discount"],
            "todays_profit": day["gross_profit"] if day else Decimal("0"),
        },
        "top_selling": list(top),
        "recent_sales": list(recent),
    }
