from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from .models import Medicine, Batch, Category, Patient
from .serializers import MedicineSerializer, BatchSerializer, CategorySerializer, PatientSerializer
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsPharmacist, IsAdmin

# Create your views here.

class MedicineViewSet(ModelViewSet):
    serializer_class = MedicineSerializer
    queryset = Medicine.objects.select_related('category').prefetch_related('batches').all()
    search_fields = ['name', 'generic_name', 'manufacturer']
    ordering_fields = ['name']
    filterset_fields = ['category', 'prescription_required']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdmin | IsPharmacist]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

class BatchViewSet(ModelViewSet):
    queryset = Batch.objects.select_related('medicine__category').all()
    serializer_class = BatchSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdmin | IsPharmacist]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

class LowStockViewSet(ReadOnlyModelViewSet):
    serializer_class = MedicineSerializer
    permission_classes = [IsAdmin | IsPharmacist]

    def get_queryset(self):
        return Medicine.objects.select_related('category').prefetch_related('batches').annotate(
            # 1. Sum up all quantity_remaining from related batches.
            # 2. Coalesce converts NULL to 0 if a medicine has zero batches.
            db_total_stock=Coalesce(Sum('batches__quantity_remaining'), 0)
        ).filter(
            # 3. Filter where the calculated stock is less than or equal to reorder_level
            db_total_stock__lte=F('reorder_level')
        )

class ExpiringSoonView(ReadOnlyModelViewSet):
    serializer_class = BatchSerializer
    permission_classes = [IsAdmin | IsPharmacist]

    def get_queryset(self):
        from django.utils.timezone import now
        from datetime import timedelta
        # Determine the number of days to look ahead for expiring batches.
        # If the 'days' query parameter is provided, use it; otherwise, default to 30 days.
        if self.request.query_params.get('days'):
            days = int(self.request.query_params.get('days'))
        else:
            days = 30

        soon_date = now() + timedelta(days=days)
        return Batch.objects.select_related('medicine__category').filter(
            expiry_date__lte=soon_date
        )

class PatientViewSet(ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    ordering_fields = ['created_at']
    search_fields = ['name', 'contact_number']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdmin | IsPharmacist]
        else:
            permission_classes = []
        return [permission() for permission in permission_classes]