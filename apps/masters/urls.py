from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("warehouses", views.WarehouseViewSet, basename="warehouse")
router.register("zones", views.ZoneViewSet, basename="zone")
router.register("racks", views.RackViewSet, basename="rack")
router.register("bins", views.BinViewSet, basename="bin")
router.register("materials", views.MaterialViewSet, basename="material")
router.register("uom", views.UnitViewSet, basename="uom")
router.register("categories", views.CategoryViewSet, basename="category")
router.register("customers", views.CustomerViewSet, basename="customer")
router.register("suppliers", views.SupplierViewSet, basename="supplier")
router.register("employees", views.EmployeeViewSet, basename="employee")
router.register("sizes", views.SizeViewSet, basename="size")
router.register("colours", views.ColourViewSet, basename="colour")
router.register("brands", views.BrandViewSet, basename="brand")
router.register("products", views.ProductViewSet, basename="product")
router.register("variants", views.ProductVariantViewSet, basename="variant")

urlpatterns = [path("", include(router.urls))]
