import re
from datetime import date

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Category, Item, Reservation, Route, SpecialRequest


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


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 07700 900123"}),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "e.g. johnsmith or johns",
            "autocomplete": "off",
        })
        self.fields["username"].help_text = None
        self.fields["password1"].widget.attrs.update({"class": "form-control"})
        self.fields["password2"].widget.attrs.update({"class": "form-control"})

    def clean_username(self):
        username = self.cleaned_data.get("username", "")
        if not re.match(r'^[a-z][a-z0-9]*$', username):
            raise forms.ValidationError(
                "Lowercase letters and numbers only, starting with a letter — no spaces or symbols."
            )
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username


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

    device_code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Samsung Galaxy A15 / IMEI 123456789"}),
    )

    sim_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 07700 900123"}),
    )

    class Meta:
        model = Item
        fields = ["category", "gender", "size"]

        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "size": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        regular = Category.objects.filter(is_special=False).order_by("name")
        special = Category.objects.filter(is_special=True).order_by("name")
        self.fields["category"].choices = [
            ("", "— Select a category —"),
            ("Regular Stock", [(c.pk, c.name) for c in regular]),
            ("Special Request", [(c.pk, c.name) for c in special]),
        ]

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        if category:
            if category.extra_field != "none":
                cleaned["quantity"] = 1
            if category.extra_field == "device_code" and not cleaned.get("device_code"):
                self.add_error("device_code", "Device code is required for this category.")
            if category.extra_field == "sim_number":
                sim = cleaned.get("sim_number", "")
                if not sim:
                    self.add_error("sim_number", "SIM number is required for this category.")
                else:
                    digits = re.sub(r"[\s\-\(\)]", "", sim)
                    if not re.match(r"^(07\d{9}|\+447\d{9})$", digits):
                        self.add_error("sim_number", "Enter a valid UK mobile number (e.g. 07700 900123 or +44 7700 900123).")
        return cleaned


# ---------------------------
# Item Edit Form (admin only — no quantity field)
# ---------------------------

class ItemEditForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ["category", "gender", "size", "device_code", "sim_number"]

        widgets = {
            "category": forms.Select(attrs={"class": "form-select"}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "size": forms.Select(attrs={"class": "form-select"}),
            "device_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "Model name and/or IMEI number"}),
            "sim_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 07700 900123"}),
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


# ---------------------------
# Special Request Form
# ---------------------------

class SpecialRequestForm(forms.ModelForm):
    class Meta:
        model = SpecialRequest
        fields = ["person", "category", "route", "notes"]

        widgets = {
            "person": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "route": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_special=True)
        self.fields["category"].empty_label = "— Select a category —"
        self.fields["route"].queryset = Route.objects.all()
        self.fields["route"].empty_label = "— Select a route —"
        self.fields["route"].required = True
        self.fields["notes"].required = False


class SpecialRequestEditForm(forms.ModelForm):
    class Meta:
        model = SpecialRequest
        fields = ["person", "route", "notes"]

        widgets = {
            "person": forms.TextInput(attrs={"class": "form-control"}),
            "route": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["route"].queryset = Route.objects.all()
        self.fields["route"].empty_label = "— Select a route —"
        self.fields["route"].required = True
        self.fields["notes"].required = False