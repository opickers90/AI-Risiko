from rest_framework import permissions


class IsSuperuserOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow Superuser only for create/edit/delete operations and read only for others.
    """

    def has_permission(self, request, view):
        """
        Checked on list and detail view.
        """
        # allow GET, HEAD or OPTIONS requests for non superuser
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        """
        Checked on detail view.
        """
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_superuser


class IsSuperuserOrOwner(permissions.BasePermission):
    """
    Custom permission to allow Superuser or Owner only for create/edit/delete operations.
    """

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return obj.user == request.user
