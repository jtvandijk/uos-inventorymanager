from datetime import date

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Item, Reservation, Route


# ---------------------------
# Authentication
# ---------------------------

class StyledLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )


# ---------------------------
# Item Form
# ---------------------------

class ItemForm(forms.ModelForm):
    quantity = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 100}),
    )

    class Meta:
        model = Item
        fields = ["category", "gender", "size"]

        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "size": forms.Select(attrs={"class": "form-select"}),
        }


# ---------------------------
# Reservation Form
# ---------------------------

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ["person", "reserved_for_date", "route", "notes"]

        widgets = {
            "person": forms.TextInput(attrs={"class": "form-control"}),
            "reserved_for_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "route": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields["reserved_for_date"].initial = date.today()

        self.fields["route"].queryset = Route.objects.all()
        self.fields["route"].empty_label = "— Select a route —"
        self.fields["route"].required = True