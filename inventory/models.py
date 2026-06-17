from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

import re


# ---------------------------
# Route
# ---------------------------

class Route(models.Model):
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7, default="#343a40")
    text_color = models.CharField(max_length=7, default="#ffffff")
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


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

    EXTRA_FIELDS = [
        ("none", "None"),
        ("device_code", "Device Code"),
        ("sim_number", "SIM Number"),
    ]

    name = models.CharField(max_length=100, unique=True)
    size_type = models.CharField(max_length=20, choices=SIZE_TYPES)
    code = models.CharField(max_length=3, blank=True)
    is_special = models.BooleanField(default=False)
    extra_field = models.CharField(max_length=20, choices=EXTRA_FIELDS, default="none")

    class Meta:
        verbose_name_plural = "Categories"

    def clean(self):
        if self.code:
            conflict = Category.objects.filter(code__iexact=self.code)
            if self.pk:
                conflict = conflict.exclude(pk=self.pk)
            if conflict.exists():
                raise ValidationError({
                    "code": f"Code '{self.code.upper()}' is already used by '{conflict.first().name}'."
                })

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.upper()
        super().save(*args, **kwargs)

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
            ("packed", "Packed"),
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

    device_code = models.CharField(max_length=100, blank=True, default="")
    sim_number = models.CharField(max_length=30, blank=True, default="")

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

        if self.category.extra_field == "device_code" and not self.device_code:
            raise ValidationError({"device_code": "Device code is required for this category."})

        if self.category.extra_field == "sim_number" and not self.sim_number:
            raise ValidationError({"sim_number": "SIM number is required for this category."})

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

    route = models.ForeignKey(
        "Route",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("reserved", "Reserved"),
            ("packed", "Packed"),
            ("given", "Given"),
            ("missed", "Missed"),
        ],
        default="reserved",
    )

    auto_extended = models.BooleanField(default=False)

    miss_reason = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=[
            ("lapsed", "Lapsed"),
            ("no_replacement", "No replacement found"),
        ],
    )

    missed_at = models.DateTimeField(null=True, blank=True)

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

        if self.status in ("reserved", "packed", "given"):
            self.item.status = self.status
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

# ---------------------------
# Special Request
# ---------------------------

class SpecialRequest(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("fulfilled", "Fulfilled"),
        ("lapsed", "Lapsed"),
    ]

    person = models.CharField(max_length=100)
    route = models.ForeignKey(
        "Route",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="special_requests",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        limit_choices_to={"is_special": True},
    )
    notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="special_requests_filed",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    last_confirmed_at = models.DateTimeField(auto_now_add=True)

    fulfilled_by_item = models.ForeignKey(
        Item,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fulfilled_special_request",
    )
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    lapsed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["requested_at"]

    def __str__(self):
        return f"{self.person} → {self.category.name} ({self.status})"


# ---------------------------
# User Profile
# ---------------------------

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True, default="")

    def __str__(self):
        return f"{self.user.username} profile"


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