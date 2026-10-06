from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("stock-in", views.StockInViewSet, basename="stock-in")
router.register("stock-out", views.StockOutViewSet, basename="stock-out")
router.register("stock-adjustments", views.StockAdjustmentViewSet, basename="stock-adjustment")
router.register("stock-movements", views.StockMovementViewSet, basename="stock-movement")

urlpatterns = [path("", include(router.urls))]
