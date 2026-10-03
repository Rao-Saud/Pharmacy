from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import re

FORM_CHOICES = [
    ('tablet', 'Tablet'),
    ('capsule', 'Capsule'),
    ('syrup', 'Syrup'),
    ('injection', 'Injection'),
    ('ointment', 'Ointment'),
]

# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Medicine(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='medicines')
    name = models.CharField(max_length=255)
    generic_name = models.CharField(max_length=255)
    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    form = models.CharField(max_length=255, choices=FORM_CHOICES, blank=True, null=True)
    strength = models.CharField(max_length=255, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    prescription_required = models.BooleanField(default=False)
    reorder_level = models.PositiveIntegerField(default=10)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'form', 'strength'], 
                name='unique_medicine')
        ]

    def __str__(self):
        return self.name

class Batch(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=255, db_index=True)
    expiry_date = models.DateField()
    quantity_remaining = models.PositiveIntegerField()
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['medicine', 'batch_number'], 
                name='unique_medicine_batch')
        ]
        ordering = ['expiry_date']

    def __str__(self):
        return f"{self.medicine.name} - {self.batch_number}"

class Patient(models.Model):
    phone_regex = RegexValidator(
        regex=r'^(?:\+92|0092|92|0)?(?:3[0-7]\d{1})\s?-?\d{7}$',
    )

    name = models.CharField(max_length=255)
    date_of_birth = models.DateField(blank=True, null=True)
    contact_number = models.CharField(max_length=14, blank=True, null=True, db_index=True, validators=[phone_regex], help_text="'03XXXXXXXXX' or '+923XXXXXXXXX'")
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Custom clean method to validate and normalize the contact number. (Ensures it follows the required format and converts it to the standard '+92XXXXXXXXX' format.)
    def clean(self):
        super().clean()
        if self.contact_number:
            num = self.contact_number.strip()
            match = re.match(r'^(?:\+92|0092|92|0)?((?:3[0-7]\d{1})\d{7})$', num)

            if match:
                core_number = match.group(1)
                self.contact_number = f'+92{core_number}'
            else:
                raise ValidationError({
                    'contact_number': "Phone number must be entered in the format: '+923XXXXXXXXX' or '03XXXXXXXXX'."
                })

    def save(self, *args, **kwargs):
        self.full_clean()  # This will call the clean() method before saving
        super().save(*args, **kwargs)
            
    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'contact_number'], 
                name='unique_patient')
        ]