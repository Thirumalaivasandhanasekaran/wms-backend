from django.db import models
from django.db.models import Case, F, Value, When

from apps.core.models import BaseModel, Status


class Warehouse(BaseModel):
    class Type(models.TextChoices):
        MAIN = "MAIN", "Main Warehouse"
        RETAIL = "RETAIL", "Retail Store"
        TRANSIT = "TRANSIT", "Transit"

    name = models.CharField(max_length=120)
    warehouse_type = models.CharField(max_length=10, choices=Type.choices, default=Type.MAIN)
    address = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=160, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "warehouses"

    def __str__(self):
        return self.name


class Zone(BaseModel):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="zones")
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "zones"
        unique_together = ("warehouse", "name")

    def __str__(self):
        return self.name


class Rack(BaseModel):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="racks")
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="racks")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "racks"
        unique_together = ("zone", "code")

    def __str__(self):
        return f"{self.code} - {self.name}"


class Bin(BaseModel):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name="bins")
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name="bins")
    rack = models.ForeignKey(Rack, on_delete=models.PROTECT, related_name="bins")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=40)
    capacity = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "bins"
        unique_together = ("rack", "code")

    def __str__(self):
        return f"{self.code} - {self.name}"


class Unit(BaseModel):
    name = models.CharField(max_length=60, unique=True)
    short_name = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "units"

    def __str__(self):
        return self.name


class Category(BaseModel):
    name = models.CharField(max_length=120, unique=True)
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Material(BaseModel):
    material_code = models.CharField(max_length=40, unique=True)
    material_name = models.CharField(max_length=160)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.PROTECT, related_name="materials")
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.PROTECT, related_name="materials")
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "materials"

    def __str__(self):
        return self.material_name


class Customer(BaseModel):
    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    name = models.CharField(max_length=120)
    mobile = models.CharField(max_length=20, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    address = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "customers"

    def __str__(self):
        return f"{self.name} ({self.mobile})" if self.mobile else self.name


class Supplier(BaseModel):
    name = models.CharField(max_length=120)
    mobile = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    gstin = models.CharField("GSTIN", max_length=20, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "suppliers"

    def __str__(self):
        return self.name


class Employee(BaseModel):
    employee_code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    mobile = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    designation = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "employees"

    def __str__(self):
        return self.name


class Size(BaseModel):
    name = models.CharField(max_length=30, unique=True)
    sort_order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "sizes"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Colour(BaseModel):
    name = models.CharField(max_length=60, unique=True)
    code = models.CharField(max_length=20, blank=True, help_text="Hex colour such as #000000")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "colours"

    def __str__(self):
        return self.name


class Brand(BaseModel):
    name = models.CharField(max_length=120, unique=True)
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "brands"

    def __str__(self):
        return self.name


class Product(BaseModel):
    product_code = models.CharField("SKU / product code", max_length=40, unique=True)
    name = models.CharField(max_length=160, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.PROTECT, related_name="products")
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", null=True, blank=True)
    minimum_stock = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        db_table = "products"

    def __str__(self):
        return self.name


class VariantQuerySet(models.QuerySet):
    """Stock status rules, used by every screen/report so they always agree.

    OUT  : current_stock == 0
    LOW  : 0 < current_stock <= minimum_stock
    IN   : current_stock > minimum_stock
    """

    def out_of_stock(self):
        return self.filter(current_stock=0)

    def low_stock(self):
        return self.filter(current_stock__gt=0, current_stock__lte=F("minimum_stock"))

    def in_stock(self):
        return self.filter(current_stock__gt=F("minimum_stock"))

    def with_status(self, code):
        return {"OUT": self.out_of_stock, "LOW": self.low_stock, "IN": self.in_stock}.get(code, lambda: self)()

    def annotate_status(self):
        return self.annotate(
            stock_status=Case(
                When(current_stock=0, then=Value("OUT")),
                When(current_stock__lte=F("minimum_stock"), then=Value("LOW")),
                default=Value("IN"),
                output_field=models.CharField(),
            )
        )


class ProductVariant(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="variants")
    size = models.ForeignKey(Size, null=True, blank=True, on_delete=models.PROTECT, related_name="variants")
    colour = models.ForeignKey(Colour, null=True, blank=True, on_delete=models.PROTECT, related_name="variants")
    sku = models.CharField(max_length=60, unique=True)
    barcode = models.CharField(max_length=60, unique=True)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    opening_stock = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=0)
    current_stock = models.IntegerField(default=0, editable=False, db_index=True)
    warehouse = models.ForeignKey(Warehouse, null=True, blank=True, on_delete=models.PROTECT, related_name="variants")
    zone = models.ForeignKey(Zone, null=True, blank=True, on_delete=models.PROTECT, related_name="variants")
    rack = models.ForeignKey(Rack, null=True, blank=True, on_delete=models.PROTECT, related_name="variants")
    bin = models.ForeignKey(Bin, null=True, blank=True, on_delete=models.PROTECT, related_name="variants")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    objects = VariantQuerySet.as_manager()

    class Meta:
        db_table = "product_variants"
        constraints = [models.UniqueConstraint(fields=["product", "size", "colour"], name="uniq_product_size_colour")]
        indexes = [models.Index(fields=["product", "status"])]

    def __str__(self):
        parts = [p.name for p in (self.size, self.colour) if p]
        return f"{self.product.name} - {' / '.join(parts)}" if parts else self.product.name

    @property
    def status_code(self):
        if self.current_stock == 0:
            return "OUT"
        return "LOW" if self.current_stock <= self.minimum_stock else "IN"
