from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django.db.models import F, Sum, ProtectedError
from django.db.models.functions import Coalesce
from .models import Medicine, Batch, Category, Patient, Prescription, PrescriptionItem, Supplier, Purchase
from .serializers import (MedicineSerializer, BatchSerializer, CategorySerializer, 
                        PatientSerializer, PharmacistReassignSerializer, PrescriptionSerializer, 
                        PrescriptionDispensedSerializer, PurchaseSerializer, SupplierSerializer)
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsPharmacist, IsAdmin
from rest_framework.generics import UpdateAPIView
from rest_framework.response import Response
from rest_framework import status, mixins, viewsets
from .services import cancel_purchase, PurchaseError
from rest_framework.decorators import action

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
    search_fields = ['medicine__name', 'batch_number']

    # def get_permissions(self):
    #     if self.action in ['create', 'update', 'partial_update', 'destroy']:
    #         permission_classes = [IsAdmin | IsPharmacist]
    #     else:
    #         permission_classes = [IsAuthenticated]
    #     return [permission() for permission in permission_classes]

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

class PrescriptionViewSet(ModelViewSet):
    queryset = Prescription.objects.select_related('patient', 'pharmacist').prefetch_related('prescriptionitem_set__medicine').all()
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAdmin | IsPharmacist]
    ordering_fields = ['created_at']
    search_fields = ['patient__name']
    filterset_fields = ['status']

    # The following block of code ensures that a warning is generated for any prescription items that do not require a prescription.
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prescription = serializer.save()

        warnings = self._check_item_warnings(prescription)

        response_data = serializer.data
        if warnings:
            response_data['warnings'] = warnings

        headers = self.get_success_headers(serializer.data)
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)


    def _check_item_warnings(self, prescription):
        warnings = []
        for item in prescription.prescriptionitem_set.select_related('medicine'):
            if not item.medicine.prescription_required:
                warnings.append(f"{item.medicine.name} does not require a prescription.")
        return warnings

class PrescriptionDispensedView(UpdateAPIView):
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionDispensedSerializer
    permission_classes = [IsAdmin | IsPharmacist]
    http_method_names = ['patch'] # Strict enforcement of partial updates


    def perform_update(self, serializer):
        # This triggers the custom update method inside your serializer
        serializer.save()

class PharmacistReassignView(UpdateAPIView):
    queryset = Prescription.objects.all()
    serializer_class = PharmacistReassignSerializer
    permission_classes = [IsAdmin]
    http_method_names = ['patch'] # Strict enforcement of partial updates

    def perform_update(self, serializer):
        # This triggers the custom update method inside your serializer
        serializer.save()

class SupplierViewSet(ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    # permission_classes = [IsAdmin]
    filterset_fields = ['active']
    search_fields = ['name']

    def destroy(self, request, *args, **kwargs):
        supplier = self.get_object()
        try:
            supplier.delete()
        except ProtectedError:
            return Response(
                {"error": "This supplier has purchases and cannot be deleted. Mark it as inactive instead."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

class PurchaseViewSet(mixins.CreateModelMixin,
                      mixins.RetrieveModelMixin,
                      mixins.ListModelMixin,
                      viewsets.GenericViewSet):
    queryset = Purchase.objects.select_related('supplier', 'user').prefetch_related('purchase_items__medicine').all()
    serializer_class = PurchaseSerializer
    permission_classes = [IsAdmin | IsPharmacist]
    ordering_fields = ['created_at']
    search_fields = ['invoice_number']
    filterset_fields = ['status']

    def get_queryset(self):
        return Purchase.objects.select_related('supplier', 'user').prefetch_related('purchase_items__medicine').all()

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        purchase = self.get_object()
        try:
            cancel_purchase(purchase=purchase, user=request.user)
        except PurchaseError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        purchase = self.get_queryset().get(pk=purchase.pk)
        return Response(self.get_serializer(purchase).data)

