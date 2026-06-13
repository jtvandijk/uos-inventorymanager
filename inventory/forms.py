from datetime import date

from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import Item, Reservation


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
        fields = ["person", "reserved_for_date", "notes"]

        widgets = {
            "person": forms.TextInput(attrs={"class": "form-control"}),
            "reserved_for_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "notes": forms.Textarea(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set default date for new reservations
        if not self.instance.pk:
            self.fields["reserved_for_date"].initial = date.today()