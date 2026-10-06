from django.db import IntegrityError
from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    if isinstance(exc, ProtectedError):
        return Response(
            {"detail": "This record is in use by other data and cannot be deleted. Set it to Inactive instead."},
            status=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, IntegrityError):
        return Response({"detail": "Database constraint violated. Check for duplicate values."}, status=400)
    return exception_handler(exc, context)
