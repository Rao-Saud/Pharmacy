from django.db import models
from django.contrib.auth.models import AbstractUser

class RoleChoices(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    PHARMACIST = 'pharmacist', 'Pharmacist'
    CASHIER = 'cashier', 'Cashier'

# Create your models here.
class CustomUser(AbstractUser):
    role = models.CharField(max_length=20, choices=RoleChoices.choices, default=RoleChoices.CASHIER)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.username
