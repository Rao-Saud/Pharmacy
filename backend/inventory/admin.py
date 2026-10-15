from django.contrib import admin
from .models import Category, Medicine, Batch, Patient, Prescription, PrescriptionItem, Supplier, Purchase, PurchaseItem

class BatchInLine(admin.TabularInline):
    model = Batch
    fields = ('batch_number', 'expiry_date', 'quantity_remaining', 'cost_price')
    extra = 1

# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'form', 'category', 'price', 'reorder_level')
    search_fields = ('name',)

    def get_inlines(self, request, obj=None):
        # Only show the BatchInLine if the Medicine object already exists. In other words, when creating a new Medicine, the inline will not be displayed.
        if obj is None:
            return []
        return [BatchInLine]

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'expiry_date', 'quantity_remaining')
    list_filter = ('expiry_date',)
    search_fields = ('batch_number',)

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_number', 'created_at')
    search_fields = ('name', 'contact_number')

class PrescriptionItemInLine(admin.TabularInline):
    model = PrescriptionItem
    fields = ('medicine', 'quantity', 'dosage_instructions')
    extra = 1

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'date_issued', 'status')
    list_filter = ('status',)
    search_fields = ('patient__name', 'doctor_name')

    def get_inlines(self, request, obj=None):
        # Only show the PrescriptionInLine if the Prescription object already exists. In other words, when creating a new Prescription, the inline will not be displayed.
        if obj is None:
            return []
        return [PrescriptionItemInLine]

@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):
    list_display = ('prescription', 'medicine', 'quantity')
    
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_number', 'active')
    search_fields = ('name', 'contact_number')

class PurchaseItemInLine(admin.TabularInline):
    model = PurchaseItem
    fields = ('medicine', 'quantity', 'unit_price', 'line_total', 'batch_number', 'expiry_date', 'batch',)
    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return ['medicine', 'quantity', 'unit_price', 'line_total', 'batch_number', 'expiry_date', 'batch']
    extra = 1

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'invoice_number', 'date', 'total_amount')
    list_filter = ('supplier',)
    search_fields = ('supplier__name',)
    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return ['supplier', 'user', 'invoice_number', 'date', 'status', 'total_amount']
    inlines = [PurchaseItemInLine]

@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ('purchase', 'medicine', 'quantity', 'unit_price')
    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return ['purchase', 'medicine', 'quantity', 'unit_price', 'line_total', 'batch_number', 'expiry_date', 'batch']