from apps.masters import models as m


def load_demo():
    """A few masters so a fresh install can be clicked through immediately. Idempotent."""
    wh, _ = m.Warehouse.objects.get_or_create(name="Main Warehouse", defaults={"address": "12 Market Road", "location": "Chennai, Tamil Nadu, India", "pincode": "600001", "contact_person": "Store Manager", "phone": "9000000000", "email": "warehouse@example.com"})
    zone, _ = m.Zone.objects.get_or_create(warehouse=wh, name="Zone A", defaults={"description": "Apparel"})
    rack, _ = m.Rack.objects.get_or_create(zone=zone, code="R1", defaults={"warehouse": wh, "name": "Rack 1"})
    m.Bin.objects.get_or_create(rack=rack, code="B1", defaults={"warehouse": wh, "zone": zone, "name": "Bin 1", "capacity": 500})
    cat, _ = m.Category.objects.get_or_create(name="Apparel")
    for name, short in (("Piece", "pc"), ("Box", "box"), ("Kg", "kg"), ("Meter", "m"), ("Set", "set")):
        m.Unit.objects.get_or_create(name=name, defaults={"short_name": short})
    for i, name in enumerate(["S", "M", "L", "XL", "XXL"], start=1):
        m.Size.objects.get_or_create(name=name, defaults={"sort_order": i})
    for name, code in (("Black", "#000000"), ("White", "#FFFFFF"), ("Blue", "#1D4ED8")):
        m.Colour.objects.get_or_create(name=name, defaults={"code": code})
    m.Brand.objects.get_or_create(name="House Brand")
    m.Supplier.objects.get_or_create(name="Sample Supplier", defaults={"mobile": "9111111111", "gstin": "33AAAAA0000A1Z5"})
    m.Customer.objects.get_or_create(name="Sample Customer", defaults={"mobile": "9222222222"})
