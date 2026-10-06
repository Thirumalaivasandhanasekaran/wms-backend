from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("sales", views.SaleViewSet, basename="sale")
router.register("sales-returns", views.SalesReturnViewSet, basename="sales-return")

urlpatterns = [path("", include(router.urls))]
