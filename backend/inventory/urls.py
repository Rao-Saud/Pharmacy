from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (MedicineViewSet, BatchViewSet, CategoryViewSet, LowStockViewSet, 
                    ExpiringSoonView, PatientViewSet, PrescriptionViewSet, 
                    PrescriptionDispensedView, PharmacistReassignView)

router = DefaultRouter()
router.register(r'medicines', MedicineViewSet)
router.register(r'batches', BatchViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'low-stock', LowStockViewSet, basename='low-stock')
router.register(r'expiring-soon', ExpiringSoonView, basename='expiring-soon')
router.register(r'patients', PatientViewSet)
router.register(r'prescriptions', PrescriptionViewSet)





urlpatterns = [
    path('', include(router.urls)),
    path('prescriptions/<int:pk>/dispense/', PrescriptionDispensedView.as_view(), name='prescription-dispense'),
    path('prescriptions/<int:pk>/reassign/', PharmacistReassignView.as_view(), name='prescription-reassign'),
]