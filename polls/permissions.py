from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        """
        Allow authenticated users only.
        """
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Allow read and creation only.
        """
        if request.method in permissions.SAFE_METHODS + ("POST",):
            return True

        return obj.author == request.user


class IsVoterOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        """
        Allow authenticated users only.
        """
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Allow vote owner only.
        """
        return obj.voter == request.user
