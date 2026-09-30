from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import CustomUser
from .serializers import CustomUserSerializer
from rest_framework.response import Response
from .permissions import IsAdmin, IsPharmacist, IsCashier, IsCustomer, IsAdminOrUser

# Create your views here.
class CustomUserListView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        if request.user.role == 'admin' and request.user.is_superuser:
            users = CustomUser.objects.all()
            serializer = CustomUserSerializer(users, many=True)
            return Response(serializer.data)
        else:
            users = CustomUser.objects.filter(id=request.user.id)
            serializer = CustomUserSerializer(users, many=True)
            return Response(serializer.data)

    def post(self, request):
        if request.user.role == 'admin' and request.user.is_superuser:
            serializer = CustomUserSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=201)
            return Response(serializer.errors, status=400)
        return Response({"detail": "You do not have permission to perform this action."}, status=403)

    # def put(self, request, pk):
    #     if request.user.role == 'admin' and request.user.is_superuser:
    #         try:
    #             user = CustomUser.objects.get(pk=pk)
    #         except CustomUser.DoesNotExist:
    #             return Response({"detail": "User not found."}, status=404)

    #         serializer = CustomUserSerializer(user, data=request.data, partial=True)
    #         if serializer.is_valid():
    #             serializer.save()
    #             return Response(serializer.data)
    #         return Response(serializer.errors, status=400)
    #     return Response({"detail": "You do not have permission to perform this action."}, status=403)

    # def delete(self, request, pk):
    #     if request.user.role == 'admin' and request.user.is_superuser:
    #         try:
    #             user = CustomUser.objects.get(pk=pk)
    #         except CustomUser.DoesNotExist:
    #             return Response({"detail": "User not found."}, status=404)

    #         user.delete()
    #         return Response(status=204)
    #     return Response({"detail": "You do not have permission to perform this action."}, status=403)

class CustomUserDetailView(APIView):
    permission_classes = [IsAdminOrUser]

    def get(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        self.check_object_permissions(request, user) # Ensure the user has permission to view this object

        serializer = CustomUserSerializer(user)
        return Response(serializer.data)
        

    def put(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        if request.user.role == 'admin' and request.user.is_superuser or request.user.id == user.id:
            serializer = CustomUserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        return Response({"detail": "You do not have permission to perform this action."}, status=403)

    def delete(self, request, pk):
        try:
            user = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        if request.user.role == 'admin' and request.user.is_superuser:
            user.delete()
            return Response({"detail": "User deleted successfully."} ,status=204)
        return Response({"detail": "You do not have permission to perform this action."}, status=403)