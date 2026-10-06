from django.contrib import admin

from . import models

admin.site.register(models.StockMovement)
admin.site.register(models.StockIn)
admin.site.register(models.StockOut)
admin.site.register(models.StockAdjustment)
