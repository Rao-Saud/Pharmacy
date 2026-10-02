from django.db import models

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