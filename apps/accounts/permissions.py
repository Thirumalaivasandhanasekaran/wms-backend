from rest_framework.permissions import BasePermission

VIEWSET_ACTIONS = {
    "list": "VIEW",
    "retrieve": "VIEW",
    "create": "CREATE",
    "update": "UPDATE",
    "partial_update": "UPDATE",
    "destroy": "DELETE",
    "export": "EXPORT",
}
METHOD_ACTIONS = {"GET": "VIEW", "HEAD": "VIEW", "OPTIONS": "VIEW", "POST": "CREATE", "PUT": "UPDATE", "PATCH": "UPDATE", "DELETE": "DELETE"}


class ModulePermission(BasePermission):
    """Enforces role permissions: view.permission_module + VIEW/CREATE/UPDATE/DELETE/EXPORT.

    A view can add custom mappings through `permission_actions = {"my_action": "UPDATE"}`.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        module = getattr(view, "permission_module", None)
        if module is None:
            return True
        mapping = {**VIEWSET_ACTIONS, **getattr(view, "permission_actions", {})}
        action = (
            mapping.get(getattr(view, "action", None))
            or mapping.get(request.method.lower())  # plain APIViews: {"get": "EXPORT"}
            or METHOD_ACTIONS.get(request.method, "VIEW")
        )
        return user.can(module, action)
