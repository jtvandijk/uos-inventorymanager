# run: exec(open("seed_random.py").read())
# run: run()

import random
from django.contrib.auth.models import User
from django.utils import timezone
from inventory.models import Item, Category, SizeOption, Reservation

def run():
    Reservation.objects.all().delete()
    Item.objects.all().delete()

    user = User.objects.first()

    categories = list(Category.objects.all())
    sizes = list(SizeOption.objects.all())

    statuses = ["available", "reserved", "given"]

    for i in range(50):
        category = random.choice(categories)

        valid_sizes = [
            s for s in sizes 
            if s.size_type == category.size_type
        ]

        if valid_sizes:
            size_value = random.choice(valid_sizes).value
        else:
            size_value = "N/A"  

        status = random.choice(statuses)

        item = Item.objects.create(
            code=f"TEST-{i:04}",
            category=category,
            gender=random.choice(["male", "female", "unisex"]),
            size=size_value,  
            status=status,
            created_by=user,
            updated_at=timezone.now()
        )

        if status == "reserved":
            Reservation.objects.create(
                item=item,
                person=f"Person {i}",
                reserved_for_date=timezone.now().date(),
                reserved_by=user
            )

        elif status == "given":
            item.given_by = user
            item.given_at = timezone.now()
            item.save()