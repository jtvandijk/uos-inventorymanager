from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.models import Item, Reservation


class Command(BaseCommand):
    help = "Extend overdue reservations by 7 days on first miss; release back to stock on second miss."

    def handle(self, *args, **options):
        today = date.today()
        released = 0
        extended = 0

        # Pass 1 first: release items on their second miss (already extended, still not collected)
        for res in Reservation.objects.filter(
            reserved_for_date__lt=today,
            status__in=["reserved", "packed"],
            auto_extended=True,
        ).select_related("item"):
            miss_note = f"Released back to stock on {today} — not collected after 7-day extension."
            new_notes = (res.notes + "\n" + miss_note) if res.notes else miss_note

            Reservation.objects.filter(pk=res.pk).update(
                status="missed",
                miss_reason="lapsed",
                missed_at=timezone.now(),
                notes=new_notes,
            )
            Item.objects.filter(pk=res.item_id).update(
                status="available",
                updated_at=timezone.now(),
            )
            released += 1
            self.stdout.write(f"  Released: {res.item.code} ({res.person}, was due {res.reserved_for_date})")

        # Pass 2: extend reservations on their first miss
        for res in Reservation.objects.filter(
            reserved_for_date__lt=today,
            status__in=["reserved", "packed"],
            auto_extended=False,
        ).select_related("item"):
            original_date = res.reserved_for_date
            new_date = original_date + timedelta(days=7)
            extend_note = f"Automated update: not collected on {original_date}, pushed to {new_date}."
            new_notes = (res.notes + "\n" + extend_note) if res.notes else extend_note

            Reservation.objects.filter(pk=res.pk).update(
                reserved_for_date=new_date,
                auto_extended=True,
                notes=new_notes,
            )
            extended += 1
            self.stdout.write(f"  Extended: {res.item.code} ({res.person}) → {new_date}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone: extended {extended} reservation(s), released {released} item(s) back to stock."
        ))
