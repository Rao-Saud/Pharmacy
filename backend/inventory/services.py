from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import F, Sum

from inventory.models import Batch

from .models import Purchase, PurchaseItem, PurchaseStatus


class PurchaseError(Exception):
    """Raised for any business-rule failure. The view turns it into a 400."""


def _validate_input(supplier, items):
    if not supplier.active:
        raise PurchaseError("This supplier is inactive.")
    if not items:
        raise PurchaseError("A purchase must contain at least one item.")

    today = date.today()
    seen = set()
    for item in items:
        if item["quantity"] < 1:
            raise PurchaseError("Item quantity must be at least 1.")
        if item["unit_price"] < 0:
            raise PurchaseError("Item price cannot be negative.")
        if item["expiry_date"] <= today:
            raise PurchaseError(
                f"Batch {item['batch_number']} of {item['medicine'].name} "
                f"has an expiry date that is not in the future."
            )
        key = (item["medicine"].pk, item["batch_number"])
        if key in seen:
            raise PurchaseError(
                f"Batch {item['batch_number']} of {item['medicine'].name} "
                f"appears more than once in this purchase."
            )
        seen.add(key)


def _get_locked_batch(item):
    """
    Find the batch for this item and lock its row, creating it (with zero
    stock) if it does not exist yet. Stock is added afterwards in one place.
    """
    lookup = {
        "medicine": item["medicine"],
        "batch_number": item["batch_number"],
    }
    
    # select_for_update() locks the row if it exists, preventing concurrent modifications
    # .first() returns the first matching batch or None if it doesn't exist yet
    batch = Batch.objects.select_for_update().filter(**lookup).first()

    if batch is None:
        try:
            # Savepoint, so an IntegrityError doesn't poison the outer transaction
            with transaction.atomic():
                batch = Batch.objects.create(
                    **lookup,
                    expiry_date=item["expiry_date"],
                    quantity_remaining=0,
                    cost_price=item["unit_price"],
                )
        except IntegrityError:
            # Another request created it at the same moment: lock and use theirs
            batch = Batch.objects.select_for_update().get(**lookup)

    if batch.expiry_date != item["expiry_date"]:
        raise PurchaseError(
            f"Batch {batch.batch_number} of {batch.medicine.name} already exists "
            f"with expiry {batch.expiry_date}, but this purchase says "
            f"{item['expiry_date']}. Fix the batch number or the date."
        )

    # Rule: an existing batch keeps its original cost_price. The price paid
    # this time is recorded on the PurchaseItem row.
    return batch


@transaction.atomic
def receive_purchase(*, supplier, user, header, purchase_items):
    """
    header: dict with invoice_number, date, total_amount, notes (optional)
    purchase_items:  list of dicts with medicine (instance), quantity, unit_price,
            batch_number, expiry_date
    Returns the saved Purchase.
    """
    _validate_input(supplier, purchase_items)

    # Fixed lock order prevents deadlocks between overlapping purchases

    purchase_items = sorted(purchase_items, key=lambda i: (i["medicine"].pk, i["batch_number"]))
    try:
        with transaction.atomic():
            purchase = Purchase.objects.create(
                supplier=supplier,
                user=user,
                invoice_number=header["invoice_number"],
                date=header["date"],
                total_amount=header["total_amount"],
                status=PurchaseStatus.RECEIVED,
            )
    except IntegrityError:
        raise PurchaseError(
            f"Invoice {header['invoice_number']} from {supplier.name} "
            f"has already been recorded."
        )

    for item in purchase_items:
        batch = _get_locked_batch(item)

        # Database-level increment: safe even if requests overlap
        Batch.objects.filter(pk=batch.pk).update(
            quantity_remaining=F("quantity_remaining") + item["quantity"]
        )

        PurchaseItem.objects.create(
            purchase=purchase,
            medicine=item["medicine"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            batch_number=item["batch_number"],
            expiry_date=item["expiry_date"],
            batch=batch,
        )

    # Final guarantee: stored total must match the saved line totals
    computed = purchase.purchase_items.aggregate(total=Sum("line_total"))["total"] or Decimal("0")
    if computed != Decimal(header["total_amount"]):
        raise PurchaseError(
            f"Invoice total {header['total_amount']} does not match the sum "
            f"of the items ({computed})."
        )

    return purchase


@transaction.atomic
def cancel_purchase(*, purchase, user):
    """
    Reverse the stock this purchase added. Refuses if any of that stock
    has already been used, so batches never go below zero.
    """
    purchase = Purchase.objects.select_for_update().get(pk=purchase.pk)

    if purchase.status == PurchaseStatus.CANCELLED:
        raise PurchaseError("This purchase is already cancelled.")

    items = list(
        purchase.purchase_items.select_related("batch", "medicine").order_by("batch_id")
    )

    # Lock all affected batches in a fixed order
    batch_ids = [i.batch_id for i in items if i.batch_id]
    locked = {
        b.pk: b
        for b in Batch.objects.select_for_update().filter(pk__in=batch_ids).order_by("pk")
    }

    # Check everything first so we never cancel half a purchase
    for item in items:
        batch = locked.get(item.batch_id)
        if batch is None:
            raise PurchaseError(
                f"{item.medicine.name} (batch {item.batch_number}) has no linked batch."
            )
        if batch.quantity_remaining < item.quantity:
            raise PurchaseError(
                f"Cannot cancel: batch {batch.batch_number} of {item.medicine.name} "
                f"has only {batch.quantity_remaining} left, but this purchase "
                f"added {item.quantity}. Some of it has already been sold."
            )

    for item in items:
        Batch.objects.filter(pk=item.batch_id).update(
            quantity_remaining=F("quantity_remaining") - item.quantity
        )

    purchase.status = PurchaseStatus.CANCELLED
    purchase.save(update_fields=["status"])
    return purchase