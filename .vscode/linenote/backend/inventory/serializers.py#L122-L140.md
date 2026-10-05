def update(self, instance, validated_data):

DRF calls update() — rather than create() — whenever the serializer is saving an existing object instead of a new one. instance is the existing Prescription row being edited (DRF fetches it from the database before calling this, typically based on the ID in the URL, like /prescriptions/14/). validated_data is the cleaned incoming data, same as in create().

items_data = validated_data.pop('items', None)

Same idea as in create(): items are pulled out separately since they're not a direct field on Prescription. The difference here is the second argument, None — this makes .pop() return None instead of raising a KeyError if items wasn't included in this particular request at all.

This matters because an update request might only want to change, say, the doctor's name, without touching the items. Making items optional on update (unlike on create, where you required at least one) means a partial edit doesn't force the client to resend the entire item list just to change one unrelated field.

if instance.status != 'pending': raise serializers.ValidationError(...)

This is the business rule from our earlier discussion: once a prescription has moved to dispensed or cancelled, it's locked. This check runs before anything is modified, so a request against a non-pending prescription fails cleanly with no partial changes — nothing gets half-updated.

One thing worth flagging: raising a ValidationError partway through update(), after DRF has already validated the incoming data but before any database writes, is safe here specifically because nothing has been saved yet at this point. If you ever add logic after instance.save() that could fail, you'd want to wrap the whole method in a database transaction so a failure can't leave the prescription half-updated — worth keeping in mind for Day 11, where sales will touch both a sale and the batches it deducts from.

for attr, value in validated_data.items(): setattr(instance, attr, value) then instance.save()

This loops over whatever fields were submitted (patient, doctor name, issued date — whichever ones the client sent) and sets each one onto the existing instance using setattr, which is a generic way of writing instance.doctor_name = value without hardcoding every field name. instance.save() then writes those changes to the database in one query.

Note this only touches fields that are present in validated_data — fields the client didn't include in the request simply aren't touched, so a partial update (PATCH) only changes what was sent, while a full update (PUT) is expected to include everything.

if items_data is not None:

This only runs the item-replacement logic if items were actually included in the request — distinguishing "the client didn't mention items" (None, skip this block) from "the client explicitly sent an empty list" ([], which would enter this block and wipe all items — worth deciding if that's the behavior you want, or if you'd rather treat an empty list as invalid, similar to the validate_items check on create).

instance.items.all().delete()

This deletes every existing PrescriptionItem currently linked to this prescription. This is the "replace wholesale" approach mentioned earlier — rather than trying to match up incoming items against existing ones (which would need some kind of item ID to know "this is the same item, just edited" versus "this is a new item"), it's simplest to just clear everything and rebuild from what was sent.

The trade-off: if a frontend form only changes one item's quantity out of three, it needs to resend all three items in the request, not just the one that changed — otherwise the other two get deleted along with the old version of the one being edited.

PrescriptionItem.objects.bulk_create([...])

Same pattern as in create() — rebuild the full set of items from items_data, each one linked to this instance via the prescription=instance argument, inserted in a single database query rather than one query per item.

return instance

DRF expects update() to return the modified instance, which it then uses to build the serialized response sent back to the client.