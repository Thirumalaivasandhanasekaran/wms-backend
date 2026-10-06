from django.urls import path

from . import views

urlpatterns = [
    path("business/", views.BusinessView.as_view()),
    path("invoice/", views.InvoiceView.as_view()),
    path("payment/", views.PaymentView.as_view()),
    path("hardware/", views.HardwareView.as_view()),
    path("public/", views.PublicSettingsView.as_view()),
    path("backup/", views.BackupView.as_view()),
]
