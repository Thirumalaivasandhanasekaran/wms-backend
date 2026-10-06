from apps.core.models import DocumentSequence


def next_barcode():
    """Unique EAN-13 style barcode (prefix 200 = in-store use) generated from a locked sequence."""
    body = f"200{DocumentSequence.next('BARCODE'):09d}"
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(body))
    return body + str((10 - total % 10) % 10)


def build_sku(product, size, colour):
    parts = [product.product_code] + [p.name for p in (size, colour) if p]
    return "-".join(parts).upper().replace(" ", "")
