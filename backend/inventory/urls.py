from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicineViewSet, BatchViewSet, CategoryViewSet, LowStockViewSet, ExpiringSoonView, PatientViewSet

router = DefaultRouter()
router.register(r'medicines', MedicineViewSet)
router.register(r'batches', BatchViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'low-stock', LowStockViewSet, basename='low-stock')
router.register(r'expiring-soon', ExpiringSoonView, basename='expiring-soon')
router.register(r'patients', PatientViewSet)



urlpatterns = [
    path('', include(router.urls)),
]