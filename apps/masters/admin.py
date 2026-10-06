from django.contrib import admin

from . import models

for model in (models.Warehouse, models.Zone, models.Rack, models.Bin, models.Unit, models.Category, models.Material,
              models.Customer, models.Supplier, models.Employee, models.Size, models.Colour, models.Brand,
              models.Product, models.ProductVariant):
    admin.site.register(model)
