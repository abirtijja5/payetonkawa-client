from rest_framework.permissions import BasePermission


class IsStaffOrSelf(BasePermission):
    """Un administrateur voit tout ; un client ne voit que sa propre fiche."""

    def has_object_permission(self, request, view, obj):
        return bool(request.user.is_staff or str(obj.id) == str(request.user.id))
