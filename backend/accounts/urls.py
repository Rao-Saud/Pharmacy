from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import CustomUserListView, CustomUserDetailView

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/<int:pk>/', CustomUserDetailView.as_view(), name='customuser_detail'),
    path('users/', CustomUserListView.as_view(), name='customuser_list_all'),
]