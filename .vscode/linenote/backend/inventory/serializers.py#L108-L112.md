This is the first part of the create() method from the PrescriptionSerializer — it handles pulling the items out and creating the parent Prescription row before any items exist. Let's go line by line.

items_data = validated_data.pop('items')

By the time create() runs, DRF has already validated the whole incoming payload and handed you validated_data — a dictionary of everything the client sent, cleaned and checked against your field definitions.

Because items is a nested serializer (a list of dictionaries, one per prescription item), it sits inside validated_data as its own key: something like

python
validated_data = {
    'patient': <Patient instance>,
    'doctor_name': 'Dr. Ahmed',
    'issued_date': date(2026, 10, 4),
    'items': [
        {'medicine': <Medicine instance>, 'quantity': 2, 'dosage': '1 tablet twice daily'},
        {'medicine': <Medicine instance>, 'quantity': 1, 'dosage': '1 tablet at night'},
    ],
}

.pop('items') does two things at once: it removes the items key from validated_data and returns its value, storing that in items_data. The removal matters because Prescription as a model has no items field — it's not a column on that table, it's a separate related model (PrescriptionItem) pointing back at it. If you tried to create a Prescription with items still in the dictionary, Django would raise an error, since Prescription.objects.create() only accepts arguments that match actual fields on the Prescription model.

So after this line: items_data holds the list of item dictionaries, and validated_data holds everything else — patient, doctor name, issued date, and so on.

validated_data['user'] = self.context['request'].user

This adds the currently logged-in user into the dictionary before creating the prescription, so you record who entered it — the pharmacist at the counter, not something the client should be allowed to set themselves (imagine a malicious or buggy frontend letting someone submit a prescription under someone else's name).

self.context is a dictionary DRF automatically gives every serializer, populated with things like the current request, when the view instantiates the serializer. self.context['request'] is that original HTTP request object, and .user is the authenticated user attached to it by your JWT authentication from Day 4 — DRF resolves this from the access token in the request's Authorization header.

This is why user was marked read_only_fields in the serializer's Meta: it's deliberately excluded from what the client can submit, and this line is where it actually gets set — server-side, not from user input.

prescription = Prescription.objects.create(**validated_data)

Now that validated_data no longer contains items and does contain user, this line creates and saves the actual Prescription row in one step — Prescription.objects.create() both builds the instance and calls .save() on it, then returns the new instance.

The ** unpacks the dictionary into keyword arguments, so this is equivalent to writing:

python
Prescription.objects.create(
    patient=validated_data['patient'],
    doctor_name=validated_data['doctor_name'],
    issued_date=validated_data['issued_date'],
    user=validated_data['user'],
)

just without hardcoding every field name — so if you add a field to the model and serializer later, this line doesn't need to change.

At this point you have a saved Prescription with its own primary key, but zero related PrescriptionItem rows yet — that's what the next part of the method (the bulk_create loop) handles, using prescription.id to link each item back to this exact row.

Why this order matters: a PrescriptionItem needs a prescription foreign key value, and that only exists once the Prescription row has been saved and has a primary key. That's the core reason this is split into two steps rather than created all at once — the parent must exist before the children can point at it.