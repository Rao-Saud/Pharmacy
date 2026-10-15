from django.db import models
from django.db.models.functions import Lower
from django.core.validators import RegexValidator, MinValueValidator
from django.core.exceptions import ValidationError
from accounts.models import CustomUser, RoleChoices
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
    batch_number = models.CharField(max_length=50, db_index=True)
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
    created_at = models.DateTimeField(auto_now_add=True) #auto_now_add sets the field to the current timestamp when the object is first created.
    updated_at = models.DateTimeField(auto_now=True) #auto_now sets the field to the current timestamp every time the object is saved.

    # Custom clean method to validate and normalize the contact number. (Ensures it follows the required format and converts it to the standard '+92XXXXXXXXX' format.)
    def clean(self):
        # Normalize the contact number before validation. Strip any leading/trailing whitespace.
        super().clean()
        if self.contact_number:
            num = self.contact_number.strip()
            match = re.match(r'^(?:\+92|0092|92|0)?((?:3[0-7]\d{1})\d{7})$', num)

            if match:
                core_number = match.group(1) # Extract the core 10-digit mobile number without any country or leading zeros. group(1) extracts the part of the number that matches the pattern inside the first set of parentheses. The ?: at the beginning of the regex makes the preceding group non-capturing.
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

STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('dispensed', 'Dispensed'),
    ('cancelled', 'Cancelled'),
]

class Prescription(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    pharmacist = models.ForeignKey(CustomUser, on_delete=models.CASCADE, limit_choices_to={'role': RoleChoices.PHARMACIST}, default=1)
    doctor_name = models.CharField(max_length=255)
    date_issued = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True) #auto_now_add sets the field to the current timestamp when the object is first created.
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"Prescription for {self.patient.name} on {self.date_issued if self.date_issued else 'N/A'}"

    class Meta:
        ordering = ['-date_issued']

class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    dosage_instructions = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.medicine.name} for {self.prescription.patient.name}"

class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    contact_number = models.CharField(max_length=15, null=True, blank=True, unique=True)
    email = models.EmailField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('name'),
                name='unique_supplier_lower'
            )
        ]

class PurchaseStatus(models.TextChoices):
    RECEIVED = 'received', 'Received'
    CANCELLED = 'cancelled', 'Cancelled'

class Purchase(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchases', db_index=True)
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='purchases')
    invoice_number = models.CharField(max_length=50, null=True, blank=True)
    date = models.DateField(db_index=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(1)])
    status = models.CharField(max_length=10, choices=PurchaseStatus.choices, default=PurchaseStatus.RECEIVED)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Purchase from {self.supplier.name} on {self.date if self.date else 'N/A'}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['supplier', 'invoice_number'], 
                name='unique_purchase')
        ]
        ordering = ['-date']

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='purchase_items')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name='purchase_items')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    line_total = models.DecimalField(max_digits=12, decimal_places=2, editable=False, default=0)
    batch_number = models.CharField(max_length=50, db_index=True)
    expiry_date = models.DateField()
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, null=True, blank=True, related_name='purchase_items')

    def save(self, *args, **kwargs):
        if self.unit_price and self.quantity:
            self.line_total = self.unit_price * self.quantity
        else:
            self.line_total = 0
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['purchase', 'medicine', 'batch_number'], 
                name='unique_purchase_item',
                ),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name='quantity_positive'
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price__gte=0),
                name='unit_price_non_negative'
            ),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.medicine.name} for {self.purchase.supplier.name}"