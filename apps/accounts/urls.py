from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

router = DefaultRouter()
router.register("users", views.UserViewSet, basename="user")
router.register("roles", views.RoleViewSet, basename="role")
router.register("permissions", views.PermissionViewSet, basename="permission")

urlpatterns = [
    path("auth/login/", views.LoginView.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("auth/me/", views.MeView.as_view()),
    path("auth/change-password/", views.ChangePasswordView.as_view()),
    path("", include(router.urls)),
]
