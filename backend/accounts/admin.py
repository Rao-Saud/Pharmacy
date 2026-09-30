from django.contrib import admin
from .models import CustomUser
from django.contrib.auth.admin import UserAdmin

class CustomUserAdmin(UserAdmin):
    # 1. Display roles and phone numbers in the main user list table
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'phone_number', 'role')
    # 2. Add filters for roles and staff status in the sidebar of the user list page
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'role') 
    # 3. Add custom fields for role and phone number in the user EDIT page
    fieldsets = list(UserAdmin.fieldsets) + [
        ('Pharmacy System Info:', {
            'classes': ('collapse',), 
            'fields' : ('role', 'phone_number')
            }
        )
    ]
    # 4. add fields for role and phone number in the user CREATION page
    add_fieldsets = list(UserAdmin.add_fieldsets) + [
        ('Pharmacy System Info:', {
            'classes': ('collapse',),
            'fields' : ('role', 'phone_number')
        }),
    ]

# Register your models here.
admin.site.register(CustomUser, CustomUserAdmin)
