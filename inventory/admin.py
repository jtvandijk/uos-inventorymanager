from django.contrib import admin
from django import forms

from .models import Item, Category, Reservation, SizeOption, Route


# ---------------------------
# Forms
# ---------------------------

class ItemAdminForm(forms.ModelForm):
    size = forms.CharField(
        required=False,
        widget=forms.Select()
    )

    class Meta:
        model = Item
        fields = "__all__"


# ---------------------------
# Item Admin
# ---------------------------

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    form = ItemAdminForm

    class Media:
        js = ("inventory/item_admin.js",)

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)


# ---------------------------
# Reservation Admin
# ---------------------------

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("item", "person", "reserved_for_date", "route", "status")

    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "item":

            # allow only available items
            queryset = Item.objects.filter(status="available")

            # include current item when editing existing reservation
            object_id = request.resolver_match.kwargs.get("object_id")

            if object_id:
                try:
                    reservation = Reservation.objects.get(pk=object_id)
                    queryset = queryset | Item.objects.filter(pk=reservation.item.pk)
                except Reservation.DoesNotExist:
                    pass

            kwargs["queryset"] = queryset

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ---------------------------
# Category Admin
# ---------------------------

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "size_type")

    class Media:
        js = ("inventory/category_admin.js",)


# ---------------------------
# Size Options Admin
# ---------------------------

@admin.register(SizeOption)
class SizeOptionAdmin(admin.ModelAdmin):
    list_display = ("value", "label", "size_type")
    list_filter = ("size_type",)


# ---------------------------
# Route Admin
# ---------------------------

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "text_color", "notes")