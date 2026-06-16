# Wipes all items and reservations, then fills with 50 realistic test records.
# Does NOT touch categories, routes, size options, or user accounts.
# Requires seed_categories.py to have been run first.
# Usage: python manage.py shell < seed_data.py

import random
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from inventory.models import Category, Item, Reservation, Route, SizeOption

NAMES = [
    "James S", "Sarah M", "Ahmed K", "Maria T", "Tom B",
    "Priya R", "Marcus L", "Sophie W", "David N", "Emma P",
    "Carlos G", "Aisha O", "Ryan H", "Natasha V", "Mohammed A",
    "Lisa C", "Kevin D", "Fatima I", "Patrick F", "Nina J",
    "George E", "Zara Q", "Connor U", "Ingrid Y", "Raj X",
    "Elena B", "Mike D", "Tamil K", "Yusuf W", "Rachel T",
]

print("Wiping items and reservations...")
Reservation.objects.all().delete()
Item.objects.all().delete()

user = User.objects.filter(is_superuser=True).first() or User.objects.first()
today = date.today()

categories = list(Category.objects.all())
routes = list(Route.objects.all())

if not categories:
    print("No categories found — run seed_categories.py first.")
    raise SystemExit

if not routes:
    print("No routes found — run seed_categories.py first.")
    raise SystemExit

clothing_sizes = list(SizeOption.objects.filter(size_type="clothing").values_list("value", flat=True))
trouser_sizes  = list(SizeOption.objects.filter(size_type="trousers").values_list("value", flat=True))
shoe_sizes     = list(SizeOption.objects.filter(size_type="shoes").values_list("value", flat=True))

size_map = {
    "clothing": clothing_sizes,
    "trousers": trouser_sizes,
    "shoes":    shoe_sizes,
    "none":     [""],
}

genders = ["male", "female", "unisex"]

# -- Create 50 items --
print("Creating 50 items...")

items = []
for _ in range(50):
    cat = random.choice(categories)
    size_pool = size_map.get(cat.size_type, [""])
    size = random.choice(size_pool) if size_pool != [""] else ""

    item = Item(
        category=cat,
        gender=random.choice(genders),
        size=size,
        created_by=user,
        updated_at=timezone.now(),
    )
    item.save()  # auto-generates UOS-XX00001 style code
    items.append(item)

# -- Distribution: ~8% reserved, ~2% packed, ~2% given, rest available --
n_reserved = 4
n_packed   = 1
n_given    = 1

shuffled = random.sample(items, len(items))
to_reserve = shuffled[:n_reserved]
to_pack    = shuffled[n_reserved:n_reserved + n_packed]
to_give    = shuffled[n_reserved + n_packed:n_reserved + n_packed + n_given]

print("Creating reservations...")

for item in to_reserve:
    days_offset = random.randint(1, 14)
    Reservation(
        item=item,
        person=random.choice(NAMES),
        reserved_for_date=today + timedelta(days=days_offset),
        route=random.choice(routes),
        reserved_by=user,
        status="reserved",
    ).save()

for item in to_pack:
    days_offset = random.randint(0, 7)
    Reservation(
        item=item,
        person=random.choice(NAMES),
        reserved_for_date=today + timedelta(days=days_offset),
        route=random.choice(routes),
        reserved_by=user,
        status="packed",
    ).save()

print("Marking collected items...")

for item in to_give:
    item.status = "given"
    item.given_by = user
    item.given_at = timezone.now()
    item.updated_at = timezone.now()
    item.save()

print(f"\nDone!")
print(f"  {Item.objects.filter(status='available').count()} available")
print(f"  {Item.objects.filter(status='reserved').count()} reserved")
print(f"  {Item.objects.filter(status='packed').count()} packed")
print(f"  {Item.objects.filter(status='given').count()} collected")
