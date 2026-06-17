# Creates categories, UK size options, and routes.
# Safe to run multiple times — uses get_or_create throughout.
# Usage: python manage.py shell < seed_categories.py

from inventory.models import Category, Item, SizeOption, Route
from django.utils import timezone

print("Setting up size options (UK sizes)...")

# Clothing — UK standard label sizes
for v in ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]:
    SizeOption.objects.get_or_create(size_type="clothing", value=v, defaults={"label": v})

# Trousers — UK waist in inches
for v in ["28", "30", "32", "34", "36", "38", "40", "42"]:
    SizeOption.objects.get_or_create(size_type="trousers", value=v, defaults={"label": v})

# Shoes — UK sizes (whole sizes)
for v in ["3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]:
    SizeOption.objects.get_or_create(size_type="shoes", value=v, defaults={"label": v})

print("Setting up categories...")

for name, code, size_type in [
    ("Jacket",       "JA", "clothing"),
    ("Coat",         "CO", "clothing"),
    ("Hoodie",       "HO", "clothing"),
    ("Jumper",       "JU", "clothing"),
    ("T-Shirt",      "TS", "clothing"),
    ("Shirt",        "SR", "clothing"),
    ("Trousers",     "TR", "trousers"),
    ("Jeans",        "JE", "trousers"),
    ("Shoes",        "SH", "shoes"),
    ("Boots",        "BO", "shoes"),
    ("Trainers",     "TN", "shoes"),
    ("Hat",          "HT", "none"),
]:
    cat, created = Category.objects.get_or_create(
        name=name,
        defaults={"code": code, "size_type": size_type},
    )
    status = "created" if created else "already exists"
    print(f"  {name} ({code}) — {status}")

print("Setting up special request categories...")

for name, code, extra_field in [
    ("Backpack",     "BP", "none"),
    ("Sleeping Bag", "SL", "none"),
    ("Tent",         "TE", "none"),
    ("Mobile Phone", "PH", "device_code"),
    ("SIM Card",     "SI", "sim_number"),
]:
    cat, created = Category.objects.get_or_create(
        name=name,
        defaults={"code": code, "size_type": "none", "is_special": True, "extra_field": extra_field},
    )
    if not created:
        # Ensure existing categories have is_special set correctly
        Category.objects.filter(pk=cat.pk).update(is_special=True, extra_field=extra_field)
    status = "created" if created else "updated"
    print(f"  {name} ({code}) — {status}")

print("Setting up routes...")

for name, color, text_color in [
    ("Embankment",  "#007D32", "#ffffff"),
    ("Hackney",     "#EE7C0E", "#000000"),
    ("Kings Cross", "#0019A8", "#ffffff"),
    ("Soho",        "#B36305", "#ffffff"),
    ("St Giles",    "#E32017", "#ffffff"),
    ("Victoria",    "#009FE0", "#ffffff"),
    ("Waterloo",    "#6BCDB2", "#000000"),
]:
    route, created = Route.objects.get_or_create(
        name=name,
        defaults={"color": color, "text_color": text_color},
    )
    status = "created" if created else "already exists"
    print(f"  {name} — {status}")

print("Adding special request stock items...")

for cat_name, device_code, sim_number in [
    ("Tent",         "",                                       ""),
    ("Mobile Phone", "Nokia 105 (4G) / IMEI 000000000000001", ""),
    ("SIM Card",     "",                                       "07700 900001"),
]:
    cat = Category.objects.get(name=cat_name)
    if not Item.objects.filter(category=cat).exists():
        item = Item(
            category=cat,
            gender="unisex",
            size="",
            device_code=device_code,
            sim_number=sim_number,
            updated_at=timezone.now(),
        )
        item.save()
        print(f"  {cat_name} ({item.code}) — created")
    else:
        print(f"  {cat_name} — already has stock, skipping")

print("\nDone.")
print(f"  {Category.objects.count()} categories")
print(f"  {Route.objects.count()} routes")
print(f"  {SizeOption.objects.count()} size options")
print(f"  {Item.objects.filter(category__is_special=True).count()} special stock item(s)")
