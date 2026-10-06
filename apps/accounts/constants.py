ACTIONS = ["VIEW", "CREATE", "UPDATE", "DELETE", "EXPORT"]

MODULES = [
    ("dashboard", "Dashboard"),
    ("users", "Users"),
    ("roles", "Roles"),
    ("permissions", "Permissions"),
    ("warehouse", "Warehouse"),
    ("zone", "Zone"),
    ("rack", "Rack"),
    ("bin", "Bin"),
    ("material", "Material"),
    ("uom", "UOM"),
    ("category", "Category"),
    ("customer", "Customer"),
    ("supplier", "Supplier"),
    ("employee", "Employee"),
    ("size", "Size"),
    ("colour", "Colour"),
    ("brand", "Brand"),
    ("product", "Product"),
    ("stock_in", "Stock In"),
    ("stock_out", "Stock Out"),
    ("stock_adjustment", "Stock Adjustment"),
    ("pos", "POS / Sales"),
    ("sales_return", "Sales Return"),
    ("reports", "Reports"),
    ("settings", "Settings"),
]

MASTER_MODULES = [
    "warehouse", "zone", "rack", "bin", "material", "uom", "category", "customer",
    "supplier", "employee", "size", "colour", "brand", "product",
]

# Default permission sets for the built-in roles (Admin / Owner gets full_access).
DEFAULT_ROLES = {
    "Admin / Owner": {"description": "Full access to everything", "full_access": True, "perms": {}},
    "Cashier": {
        "description": "Runs the POS, handles returns, looks up masters",
        "full_access": False,
        "perms": {
            "dashboard": ["VIEW"],
            **{m: ["VIEW"] for m in MASTER_MODULES},
            "customer": ["VIEW", "CREATE", "UPDATE"],
            "pos": ["VIEW", "CREATE"],
            "sales_return": ["VIEW", "CREATE"],
            "reports": ["VIEW"],
            "settings": ["VIEW"],
        },
    },
    "Stock Staff": {
        "description": "Receives and adjusts stock, maintains product masters",
        "full_access": False,
        "perms": {
            "dashboard": ["VIEW"],
            **{m: ["VIEW", "CREATE", "UPDATE", "EXPORT"] for m in MASTER_MODULES if m not in ("customer", "employee")},
            "customer": ["VIEW"],
            "employee": ["VIEW"],
            "stock_in": ["VIEW", "CREATE", "EXPORT"],
            "stock_out": ["VIEW", "CREATE", "EXPORT"],
            "stock_adjustment": ["VIEW", "CREATE", "EXPORT"],
            "reports": ["VIEW", "EXPORT"],
            "settings": ["VIEW"],
        },
    },
}
