from rest_framework import serializers
from .models import FORM_CHOICES, Medicine, Batch, Category

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
    medicine = serializers.PrimaryKeyRelatedField(queryset=Medicine.objects.all())

    # Include the form field for the batch, which is write-only and optional.
    form = serializers.ChoiceField(choices=FORM_CHOICES, write_only=True, required=False)

    class Meta:
        model = Batch
        fields = '__all__'

    def _handle_medicine_form(self, validated_data):
        """Helper method to extract form and update the medicine instance."""
        form = validated_data.pop('form', None)
        medicine_instance = validated_data['medicine']
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