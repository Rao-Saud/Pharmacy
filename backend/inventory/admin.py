from django.contrib import admin
from .models import Category, Medicine, Batch

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
        if obj is None:
            return []
        return [BatchInLine]

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('medicine', 'expiry_date', 'quantity_remaining')
    list_filter = ('expiry_date',)
    search_fields = ('batch_number',)
