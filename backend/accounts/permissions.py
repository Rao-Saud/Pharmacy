from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )

class IsPharmacist(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'pharmacist'

class IsCashier(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'cashier'

class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

class IsAdminOrUser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        is_admin = request.user.is_authenticated and request.user.role == 'admin'
        is_user = request.user.is_authenticated and request.user.id == obj.pk
        return is_admin or is_user