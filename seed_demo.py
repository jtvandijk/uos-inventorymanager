# Sets up demo scenarios on top of the fake stock:
#   - a phone queue (waiting 9 weeks, 3 weeks, 2 days) with no phones in stock,
#     so adding a phone live shows it going to the longest-waiting person
#   - sleeping bag and backpack queues with nothing in stock (Overview shortfall)
#   - today's Waterloo walk (3 collections, 1 packed) and 2 for next week
#   - one reservation on its grace week (orange clock icon)
#   - 3 months of history (items handed out, missed collections) for the impact numbers
# Usage, after seed_data.py and seed_categories.py:
#   python manage.py shell < seed_demo.py

import random
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from inventory.models import Category, Item, Reservation, Route, SpecialRequest

rng = random.Random(42)
today = date.today()
now = timezone.now()

admin = User.objects.filter(is_superuser=True).first() or User.objects.first()
volunteer = User.objects.filter(is_active=True, is_superuser=False).exclude(groups__name="Admin").first() or admin
waterloo = Route.objects.get(name="Waterloo")
routes = list(Route.objects.all())

if Item.objects.filter(status="available", category__is_special=False).count() < 40:
    print("Not enough stock — run seed_data.py first.")
    raise SystemExit


def available_items(n):
    pool = list(Item.objects.filter(status="available", category__is_special=False))
    return rng.sample(pool, n)


def special_request(person, category_name, days_ago, confirmed_days_ago=None):
    sr = SpecialRequest.objects.create(
        person=person, category=Category.objects.get(name=category_name),
        route=waterloo, requested_by=volunteer, notes="",
    )
    # requested_at / last_confirmed_at are auto_now_add, so backdate with update()
    SpecialRequest.objects.filter(pk=sr.pk).update(
        requested_at=now - timedelta(days=days_ago),
        last_confirmed_at=now - timedelta(days=confirmed_days_ago if confirmed_days_ago is not None else days_ago),
    )


print("Special request queues (no stock, so they wait)...")
Item.objects.filter(category__name__in=["Mobile Phone", "Sleeping Bag", "Backpack"], status="available").delete()
special_request("Marek D", "Mobile Phone", 63, confirmed_days_ago=12)
special_request("Grace O", "Mobile Phone", 22, confirmed_days_ago=5)
special_request("Tom W", "Mobile Phone", 2)
special_request("Ahmed K", "Sleeping Bag", 30, confirmed_days_ago=8)
special_request("Lisa C", "Sleeping Bag", 10)
special_request("Sophie W", "Backpack", 15, confirmed_days_ago=3)

print("Today's Waterloo walk and next week...")
for i, (item, person) in enumerate(zip(available_items(3), ["James S", "Maria T", "Ryan H"])):
    Reservation(item=item, person=person, route=waterloo, reserved_for_date=today,
                reserved_by=volunteer, status="packed" if i == 0 else "reserved").save()
for item, person in zip(available_items(2), ["Nina J", "Carlos G"]):
    Reservation(item=item, person=person, route=waterloo, reserved_for_date=today + timedelta(days=7),
                reserved_by=volunteer).save()

print("A reservation on its grace week...")
[item] = available_items(1)
res = Reservation(item=item, person="Patrick F", route=waterloo, reserved_for_date=today + timedelta(days=3),
                  reserved_by=volunteer)
res.save()
Reservation.objects.filter(pk=res.pk).update(
    auto_extended=True,
    notes=f"Automated update: not collected on {today - timedelta(days=4)}, pushed to {today + timedelta(days=3)}.",
)

print("Three months of history...")
people = ["Kevin D", "Fatima I", "George E", "Zara Q", "Connor U", "Ingrid Y", "Raj X", "Elena B",
          "Mike D", "Yusuf W", "Rachel T", "Aisha O", "Marcus L", "Emma P"]
for item in available_items(24):
    when = now - timedelta(days=rng.randint(1, 90))
    Reservation(item=item, person=rng.choice(people), route=rng.choice(routes),
                reserved_for_date=when.date(), reserved_by=volunteer, status="given").save()
    Item.objects.filter(pk=item.pk).update(status="given", given_by=volunteer, given_at=when, updated_at=when)

for days_ago, reason in [(40, "lapsed"), (25, "lapsed"), (6, "no_replacement")]:
    [item] = available_items(1)
    res = Reservation(item=item, person=rng.choice(people), route=rng.choice(routes),
                      reserved_for_date=today - timedelta(days=days_ago + 7), reserved_by=volunteer)
    res.save()
    Reservation.objects.filter(pk=res.pk).update(
        status="missed", miss_reason=reason, missed_at=now - timedelta(days=days_ago),
        notes="Demo: missed collection.",
    )
    if reason == "no_replacement":
        Item.objects.filter(pk=item.pk).update(status="given", given_by=volunteer, given_at=now - timedelta(days=days_ago))
    else:
        Item.objects.filter(pk=item.pk).update(status="available")

print("\nDone.")
print(f"  Phone queue: {SpecialRequest.objects.filter(category__name='Mobile Phone', status='active').count()} waiting, "
      f"{Item.objects.filter(category__name='Mobile Phone', status='available').count()} in stock")
print(f"  Today's walk (Waterloo): {Reservation.objects.filter(reserved_for_date=today, route=waterloo, status__in=['reserved', 'packed']).count()} collections")
print(f"  Handed out in the last 90 days: {Item.objects.filter(status='given', given_at__gte=now - timedelta(days=90)).count()}")
print("  Demo: as admin, add a Mobile Phone — it goes to Marek D (waiting 9 weeks), not Tom W (2 days).")
