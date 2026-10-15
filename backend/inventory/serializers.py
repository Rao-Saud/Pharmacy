from rest_framework import serializers
from .models import (FORM_CHOICES, Medicine, Batch, Category, Patient, Prescription, 
                    PrescriptionItem, Purchase, Supplier, PurchaseItem)
from django.db import transaction
from accounts.models import CustomUser, RoleChoices
from django.utils import timezone
from decimal import Decimal
from .services import receive_purchase, PurchaseError

class MedicineSerializer(serializers.ModelSerializer):
    total_stock = serializers.SerializerMethodField()

    class Meta:
        model = Medicine
        fields = [
        'id', 'category', 'name', 'generic_name', 'manufacturer',
        'form', 'strength', 'price', 'prescription_required',
        'reorder_level', 'total_stock',
    ]

    # Calculate the total stock of the medicine by summing the quantity remaining in all its batches.
    def get_total_stock(self, obj):
        return sum(batch.quantity_remaining for batch in obj.batches.all())

class MedicineMinimalSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Medicine
        fields = ['id', 'name', 'category', 'form']


class BatchSerializer(serializers.ModelSerializer):
    # Include the medicine's form in the batch serializer for reference.
    medicine = serializers.PrimaryKeyRelatedField(queryset=Medicine.objects.all())

    # Include the form field for the batch, which is write-only and optional.
    form = serializers.ChoiceField(choices=FORM_CHOICES, write_only=True, required=False)

    class Meta:
        model = Batch
        fields = '__all__'

    def _handle_medicine_form(self, validated_data):
        """Helper method to extract form and update the medicine instance."""
        # validated_data is a dictionary containing the data to be used for creating or updating a Batch instance.
        form = validated_data.pop('form', None)
        medicine_instance = validated_data['medicine']
        # If the form is not provided, retain the existing form of the medicine instance.
        if form and medicine_instance:
            medicine_instance.form = form
            medicine_instance.save(update_fields=['form'])


    def create(self, validated_data):
        self._handle_medicine_form(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # If 'medicine' isn't explicitly provided in a PATCH request, 
        # look up the current medicine attached to this batch instance
        if 'form' in validated_data and 'medicine' not in validated_data:
            validated_data['medicine'] = instance.medicine

        self._handle_medicine_form(validated_data)
        return super().update(instance, validated_data)

    # Override the default representation of the Batch instance to include detailed medicine information.
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['medicine'] = MedicineMinimalSerializer(instance.medicine).data
        return representation

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = '__all__'

class PrescriptionItemSerializer(serializers.ModelSerializer):
    # source attribute specifies the attribute on the model instance that should be used to populate this field. Here, 'medicine.name' means we are accessing the 'name' attribute of the related 'medicine' object.
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)

    class Meta:
        model = PrescriptionItem
        fields = ['id', 'medicine', 'medicine_name', 'quantity', 'dosage_instructions']

    # validate_<field_name> is a DRF convention for field-specific validation methods. Here, we are validating the 'quantity' field.
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

class PrescriptionSerializer(serializers.ModelSerializer):
    # source = 'prescriptionitem_set' specifies that the items field should be populated using the related PrescriptionItem instances associated with this Prescription.
    items = PrescriptionItemSerializer(many=True, source='prescriptionitem_set')
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    class Meta:
        model = Prescription
        fields = ['id', 'patient', 'patient_name', 'pharmacist', 'doctor_name', 
                  'status', 'date_issued', 'created_at', 'items']
        read_only_fields = ['status', 'pharmacist', 'created_at']

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("A prescription must have at least one item.")
        return value

    def create(self, validated_data):
        # set items_data to the related PrescriptionItem instances
        items_data = validated_data.pop('prescriptionitem_set')
        # add the current user(pharmacist) to the validated data before creating the Prescription instance
        validated_data['pharmacist'] = self.context['request'].user
        # create PrescriptionItem instances for each item in items_data
        prescription = Prescription.objects.create(**validated_data)

        # use bulk_create to efficiently create all PrescriptionItem instances at once
        PrescriptionItem.objects.bulk_create([
            PrescriptionItem(prescription=prescription, **item_data) for item_data in items_data
        ])
        return prescription

    def update(self, instance, validated_data):
        items_data = validated_data.pop('prescriptionitem_set', None)
        
        if instance.status != 'pending':
            raise serializers.ValidationError("Only pending prescriptions can be updated.")

        with transaction.atomic():
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if items_data is not None:
                # Delete existing items and create new ones
                instance.prescriptionitem_set.all().delete()
                PrescriptionItem.objects.bulk_create([
                    PrescriptionItem(prescription=instance, **item_data) for item_data in items_data
                ])

        return instance

class PrescriptionDispensedSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Prescription
        # Keep fields empty or read-only because the user doesn't pass raw data;
        # the backend handles the state change automatically.
        fields = []

    def update(self, instance, validated_data):
        if instance.status != 'pending':
            raise serializers.ValidationError({"status": "Only pending prescriptions can be marked as dispensed."})

        instance.status = 'dispensed'
        instance.save(update_fields=['status'])
        return instance

class PharmacistReassignSerializer(serializers.ModelSerializer):
    pharmacist = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())

    class Meta:
        model = Prescription
        fields = ['pharmacist']

    def validate_pharmacist(self, value):
        if value and getattr(value, 'role', None) != RoleChoices.PHARMACIST:
            raise serializers.ValidationError("The assigned user must be a pharmacist.")
        return value

    def update(self, instance, validated_data):
        instance.pharmacist = validated_data.get('pharmacist', instance.pharmacist)
        instance.save(update_fields=['pharmacist'])
        return instance

class SupplierSerializer(serializers.ModelSerializer):
    active = serializers.BooleanField(default=True)

    class Meta:
        model = Supplier
        fields = ['name', 'active', 'contact_number', 'address', 'email']

    def validate_name(self, value):
        instance = self.instance
        queryset = Supplier.objects.filter(name__iexact=value)
        # if updating an existing instance, exclude it from the uniqueness check
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("A supplier with this name already exists.")
        return value

class PurchaseItemSerializer(serializers.ModelSerializer):
    medicine = serializers.PrimaryKeyRelatedField(queryset=Medicine.objects.select_related('category').all())
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    batch_number = serializers.CharField(max_length=255)
    expiry_date = serializers.DateField()
    

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be a positive integer.")
        return value

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit price must be a non-negative number.")
        return value

    def validate_expiry_date(self, value):
        if value <= timezone.localdate():
            raise serializers.ValidationError("Expiry date must be in the future.")
        return value

    class Meta:
        model = PurchaseItem
        fields = ['purchase', 'medicine', 'quantity', 'unit_price', 'line_total', 'batch_number', 'expiry_date', 'batch']
        read_only_fields = ['purchase', 'line_total', 'batch']

class PurchaseSerializer(serializers.ModelSerializer):
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    purchase_items = PurchaseItemSerializer(many=True)

    class Meta:
        model = Purchase
        fields = ['id', 'supplier', 'user', 'invoice_number', 'date', 'total_amount', 'status', 'created_at', 'purchase_items']
        read_only_fields = ['id', 'user', 'status', 'created_at']

    def validate_supplier(self, value):
        if value.active is False:
            raise serializers.ValidationError("The selected supplier is not active.")
        return value

    def validate_purchase_items(self, items):
        if not items:
            raise serializers.ValidationError("At least one purchase item is required.")

        seen = set()
        for item in items:
            key = (item['medicine'].pk, item['batch_number'].strip())
            if key in seen:
                raise serializers.ValidationError(f"Batch {item['batch_number']} for medicine {item['medicine'].name} appears more than once.")
            seen.add(key)
        return items

    def validate(self, attrs):
        items = attrs.get('purchase_items', [])
        computed_total = sum(
            (Decimal(i["quantity"]) * i["unit_price"] for i in items),
            Decimal("0"),
        )
        if 'total_amount' in attrs and attrs['total_amount'] != computed_total:
            raise serializers.ValidationError(f"total_amount: Invoice Total {attrs['total_amount']} does not match the sum of purchase items {computed_total}.")
        return attrs

    def create(self, validated_data):
        purchase_items = validated_data.pop('purchase_items')
        supplier = validated_data.pop('supplier')
        user = self.context['request'].user

        try:
            purchase = receive_purchase(
                supplier=supplier,
                user=user,
                header=validated_data,
                purchase_items=purchase_items,
            )
        except PurchaseError as e:
            raise serializers.ValidationError({"detail": str(e)})

        return purchase

    def update(self, instance, validated_data):
        raise serializers.ValidationError({"detail": "Purchases cannot be edited. Cancel the purchase and create a new one."})

        
        