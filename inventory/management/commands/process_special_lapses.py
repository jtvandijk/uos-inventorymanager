from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.models import Item, Reservation, SpecialRequest


def _next_walk_day(weekday):
    today = date.today()
    days = (weekday - today.weekday()) % 7 or 7
    return today + timedelta(days=days)


class Command(BaseCommand):
    help = "Lapse stale special requests (no confirmation in 4 weeks) and re-assign freed special-category items."

    def handle(self, *args, **options):
        today = date.today()
        cutoff = timezone.now() - timedelta(days=28)
        lapsed = 0
        assigned = 0

        # Pass 1: lapse requests not confirmed in 4 weeks
        stale = SpecialRequest.objects.filter(status="active", last_confirmed_at__lt=cutoff)
        lapsed = stale.count()
        stale.update(status="lapsed", lapsed_at=timezone.now())
        if lapsed:
            self.stdout.write(f"  Lapsed {lapsed} stale special request(s).")

        # Pass 2: auto-assign any available special-category items to the queue
        special_items = Item.objects.filter(
            category__is_special=True,
            status="available",
        ).select_related("category")

        for item in special_items:
            req = SpecialRequest.objects.filter(
                category=item.category,
                status="active",
            ).order_by("requested_at").first()

            if not req:
                continue

            collection_date = _next_walk_day(req.requested_at.weekday())

            res = Reservation(
                item=item,
                person=req.person,
                route=req.route,
                reserved_for_date=collection_date,
                notes=f"Special request auto-assigned (originally requested {req.requested_at.date()}).",
                reserved_by=req.requested_by,
            )
            res.save()

            SpecialRequest.objects.filter(pk=req.pk).update(
                status="fulfilled",
                fulfilled_at=timezone.now(),
                fulfilled_by_item=item,
            )
            assigned += 1
            self.stdout.write(f"  Assigned: {item.code} → {req.person} ({req.category.name}), collect {collection_date}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone: lapsed {lapsed} request(s), auto-assigned {assigned} item(s)."
        ))
