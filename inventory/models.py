from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

import re


# ---------------------------
# Category
# ---------------------------

class Category(models.Model):
    SIZE_TYPES = [
        ("clothing", "Clothing"),
        ("trousers", "Trousers"),
        ("shoes", "Shoes"),
        ("none", "No Size"),
    ]

    name = models.CharField(max_length=100, unique=True)
    size_type = models.CharField(max_length=20, choices=SIZE_TYPES)
    code = models.CharField(max_length=3, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


# ---------------------------
# Item
# ---------------------------

class Item(models.Model):
    code = models.CharField(max_length=50, unique=True, blank=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT
    )

    gender = models.CharField(
        max_length=10,
        choices=[
            ("male", "Male"),
            ("female", "Female"),
            ("unisex", "Unisex"),
        ],
        default="unisex",
    )

    size = models.CharField(max_length=20, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("available", "Available"),
            ("reserved", "Reserved"),
            ("given", "Given"),
        ],
        default="available",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items_created",
    )

    given_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items_given",
    )

    updated_at = models.DateTimeField(null=True, blank=True)
    given_at = models.DateTimeField(null=True, blank=True)

    def get_size_label(self):
        if not self.size:
            return None

        size_option = SizeOption.objects.filter(
            value=self.size,
            size_type=self.category.size_type
        ).first()

        return size_option.label if size_option else self.size

    def clean(self):
        if not self.category:
            return

        size_type = self.category.size_type

        if size_type != "none" and not self.size:
            raise ValidationError({
                "size": "Size is required for this category"
            })

        if not self.size:
            return

        valid = SizeOption.objects.filter(
            value=self.size,
            size_type=size_type
        ).exists()

        if not valid:
            raise ValidationError({
                "size": f"Invalid size '{self.size}' for category '{self.category.name}'"
            })

    def generate_code(self):
        prefix = "UOS"
        cat_code = self.category.code.upper() if self.category.code else "XX"

        last_item = Item.objects.filter(
            category=self.category
        ).order_by("-code").first()

        if last_item and last_item.code:
            match = re.search(r"(\d+)$", last_item.code)
            last_number = int(match.group(1)) if match else 0
        else:
            last_number = 0

        new_number = str(last_number + 1).zfill(5)

        return f"{prefix}-{cat_code}{new_number}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} ({self.category})"


# ---------------------------
# Reservation
# ---------------------------

class Reservation(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    person = models.CharField(max_length=100)
    reserved_for_date = models.DateField()
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("reserved", "Reserved"),
            ("packed", "Packed"),
            ("given", "Given"),
        ],
        default="reserved",
    )

    reserved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations_made",
    )

    def __str__(self):
        return f"{self.person} → {self.item.code}"

    def clean(self):
        if not self.item_id:
            return

        existing = Reservation.objects.filter(
            item=self.item,
            status="reserved"
        )

        if self.pk:
            existing = existing.exclude(pk=self.pk)

        if existing.exists():
            raise ValidationError({
                "item": "This item is already reserved"
            })

    def save(self, *args, **kwargs):
        self.full_clean()

        if self.status == "reserved":
            self.item.status = "reserved"
            self.item.updated_at = timezone.now()
            self.item.save()

        elif self.status == "given":
            self.item.status = "given"
            self.item.updated_at = timezone.now()
            self.item.save()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.item.status = "available"
        self.item.updated_at = timezone.now()
        self.item.save()

        super().delete(*args, **kwargs)


# ---------------------------
# Size Options
# ---------------------------

class SizeOption(models.Model):
    SIZE_TYPES = [
        ("clothing", "Clothing"),
        ("trousers", "Trousers"),
        ("shoes", "Shoes"),
    ]

    size_type = models.CharField(max_length=20, choices=SIZE_TYPES)
    value = models.CharField(max_length=20)
    label = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.label} ({self.size_type})"