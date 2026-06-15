from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse, HttpResponseRedirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.contrib import messages

from .models import Category, SizeOption, Item, Reservation, Route
from .forms import ItemForm, ItemEditForm, ReservationForm

import re


# ---------------------------
# Permissions & Context
# ---------------------------

def is_admin(user):
    return user.groups.filter(name="Admin").exists()


def add_role_context(request, context):
    context["is_admin"] = is_admin(request.user)
    return context


# ---------------------------
# AJAX — Size Options
# ---------------------------

def get_sizes(request):
    category_id = request.GET.get("category_id")

    if not category_id:
        return JsonResponse({"sizes": []})

    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return JsonResponse({"sizes": []})

    sizes = list(SizeOption.objects.filter(size_type=category.size_type))

    clothing_order = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]

    def sort_key(size):
        value = size.value.upper()

        try:
            return (0, float(value))
        except ValueError:
            pass

        if value in clothing_order:
            return (1, clothing_order.index(value))

        return (2, value)

    sizes = sorted(sizes, key=sort_key)

    return JsonResponse({
        "sizes": [{"value": s.value, "label": s.label} for s in sizes]
    })


# ---------------------------
# Inventory (Admin)
# ---------------------------

@login_required
def inventory_view(request):

    if not is_admin(request.user):
        return redirect("volunteer")

    items = Item.objects.select_related("category").prefetch_related("reservation_set")

    status = request.GET.get("status")
    search = request.GET.get("search")
    sort = request.GET.get("sort", "code")

    if status:
        items = items.filter(status=status)
    else:
        items = items.exclude(status="given")

    if search:
        # Search by item code, category name, or the name on a reservation
        items = items.filter(
            Q(code__icontains=search) |
            Q(category__name__icontains=search) |
            Q(reservation__person__icontains=search)
        ).distinct()

    allowed_sorts = [
        "code", "-code",
        "category__name", "-category__name",
        "gender", "-gender",
        "size", "-size",
        "status", "-status",
    ]

    if sort == "pickup":
        items = items.order_by("reservation__reserved_for_date")
    elif sort == "-pickup":
        items = items.order_by("-reservation__reserved_for_date")
    elif sort in allowed_sorts:
        items = items.order_by(sort)

    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "sort": sort,
    }

    return render(
        request,
        "inventory/inventory.html",
        add_role_context(request, context),
    )


# ---------------------------
# Item Detail
# ---------------------------

@login_required
def view_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)

    reservation = Reservation.objects.filter(
        item=item,
        status__in=["reserved", "packed"],
    ).first()

    next_url = request.GET.get("next", "/inventory/")

    context = {
        "item": item,
        "reservation": reservation,
        "next": next_url,  
    }

    return render(
        request,
        "inventory/view_item.html",
        add_role_context(request, context),
    )


# ---------------------------
# Reservation Actions
# ---------------------------

@login_required
def reserve_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)

    next_url = request.GET.get("next") or request.POST.get("next") or "/inventory/"

    if item.status != "available":
        return redirect(next_url)

    if request.method == "POST":
        form = ReservationForm(request.POST)

        if form.is_valid():
            Reservation.objects.filter(item=item).delete()

            reservation = form.save(commit=False)
            reservation.item = item
            reservation.reserved_by = request.user
            reservation.save()

            item.status = "reserved"
            item.updated_at = timezone.now()
            item.save()

            messages.success(request, f"Item {item.code} reserved successfully")

            return redirect(next_url)
    else:
        form = ReservationForm()

    context = {
        "form": form,
        "item": item,
        "next": next_url,
    }

    return render(
        request,
        "inventory/reserve_item.html",
        add_role_context(request, context),
    )


@login_required
def edit_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)

    if reservation.reserved_by != request.user and not is_admin(request.user):
        return redirect("inventory")

    item = reservation.item
    next_url = request.GET.get("next") or request.POST.get("next") or "/inventory/"

    if request.method == "POST":
        form = ReservationForm(request.POST, instance=reservation)
        if form.is_valid():
            form.save()
            messages.success(request, f"Reservation for {reservation.person} updated.")
            from django.urls import reverse
            return redirect(f"{reverse('view_item', args=[item.id])}?next={next_url}")
    else:
        form = ReservationForm(instance=reservation)

    context = {
        "form": form,
        "item": item,
        "reservation": reservation,
        "next": next_url,
    }
    return render(request, "inventory/edit_reservation.html", add_role_context(request, context))


@login_required
def cancel_reservation(request, item_id):
    item = get_object_or_404(Item, id=item_id)

    reservation = Reservation.objects.filter(
        item=item,
        status__in=["reserved", "packed"],
    ).first()

    if reservation and (
        reservation.reserved_by == request.user or is_admin(request.user)
    ):
        reservation.delete()

    return redirect(request.GET.get("next") or "/inventory/")


@login_required
def pack_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    next_url = request.GET.get("next") or request.POST.get("next") or "/inventory/"

    reservation = Reservation.objects.filter(
        item=item,
        status__in=["reserved", "packed"],
    ).first()

    if reservation:
        reservation.status = "packed" if reservation.status == "reserved" else "reserved"
        reservation.save()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": reservation.status if reservation else ""})

    return redirect(next_url)


@login_required
def collect_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)

    if item.status in ("reserved", "packed"):
        Reservation.objects.filter(item=item).delete()

        item.status = "given"
        item.given_by = request.user
        item.given_at = timezone.now()
        item.updated_at = timezone.now()
        item.save()

    return redirect(request.GET.get("next", "/inventory/"))


# ---------------------------
# Admin Actions
# ---------------------------

@user_passes_test(is_admin)
@login_required
def add_item(request):

    if request.method == "POST":
        form = ItemForm(request.POST)

        if form.is_valid():
            quantity = form.cleaned_data["quantity"]
            category = form.cleaned_data["category"]
            gender = form.cleaned_data["gender"]
            size = form.cleaned_data.get("size", "")

            created_codes = []
            for _ in range(quantity):
                item = Item(
                    category=category,
                    gender=gender,
                    size=size,
                    created_by=request.user,
                    updated_at=timezone.now(),
                )
                item.save()
                created_codes.append(item.code)

            from django.urls import reverse
            codes_param = ",".join(created_codes)
            return redirect(reverse("add_item_confirm") + f"?codes={codes_param}")
    else:
        form = ItemForm()

    context = {"form": form}

    return render(
        request,
        "inventory/add_item.html",
        add_role_context(request, context),
    )


@user_passes_test(is_admin)
@login_required
def add_item_confirm(request):
    raw = request.GET.get("codes", "")
    codes = [c.strip() for c in raw.split(",") if c.strip()]

    context = {"codes": codes}
    return render(
        request,
        "inventory/add_item_confirm.html",
        add_role_context(request, context),
    )


@user_passes_test(is_admin)
@login_required
def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    next_url = request.GET.get("next") or request.POST.get("next") or "/inventory/"

    if request.method == "POST":
        form = ItemEditForm(request.POST, instance=item)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_at = timezone.now()
            updated.save()
            messages.success(request, f"Item {item.code} updated.")
            from django.urls import reverse
            return redirect(f"{reverse('view_item', args=[item_id])}?next={next_url}")
    else:
        form = ItemEditForm(instance=item)

    context = {
        "form": form,
        "item": item,
        "next": next_url,
    }
    return render(request, "inventory/edit_item.html", add_role_context(request, context))


@user_passes_test(is_admin)
@login_required
def delete_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    item.delete()

    return redirect(request.GET.get("next", "/inventory/"))


# ---------------------------
# Volunteer View (AJAX)
# ---------------------------

@login_required
def volunteer_view(request):

    status_filter = request.GET.get("status", "available")
    search = request.GET.get("search", "")

    items = Item.objects.filter(
        status=status_filter
    ).select_related("category").prefetch_related("reservation_set")

    if search:
        # Allow volunteers to find items by category, ID, or the name on a reservation
        # (e.g. a client says "I reserved a sweater" — search their name directly)
        items = items.filter(
            Q(category__name__icontains=search) |
            Q(code__icontains=search) |
            Q(reservation__person__icontains=search)
        ).distinct()

    paginator = Paginator(items.order_by("code"), 5)
    page_obj = paginator.get_page(request.GET.get("page"))

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string(
            "inventory/_item_list.html",
            {"page_obj": page_obj, "status_filter": status_filter},
            request=request,
        )
        return JsonResponse({"html": html})

    my_res = Reservation.objects.filter(
        reserved_by=request.user,
        status="reserved"
    )

    res_page_obj = Paginator(my_res.order_by("-id"), 5).get_page(
        request.GET.get("res_page")
    )

    context = {
        "page_obj": page_obj,
        "my_reservations": res_page_obj,
        "res_page_obj": res_page_obj,
        "search": search,
        "status_filter": status_filter,
    }

    return render(
        request,
        "inventory/volunteer.html",
        add_role_context(request, context),
    )


# ---------------------------
# Run Sheet
# ---------------------------

@login_required
def run_sheet_view(request):
    if not is_admin(request.user):
        return redirect("volunteer")

    from datetime import date as date_type

    routes = Route.objects.all()
    today = date_type.today().isoformat()
    date_str = request.GET.get("date", today)
    route_id = request.GET.get("route", "")

    reservations = None
    selected_date = None
    selected_route = None

    if date_str:
        try:
            selected_date = date_type.fromisoformat(date_str)
            qs = Reservation.objects.filter(
                reserved_for_date=selected_date,
                status__in=["reserved", "packed"],
            ).select_related("item", "item__category", "route").order_by(
                "item__category__name", "item__code"
            )

            if route_id:
                qs = qs.filter(route_id=route_id)
                selected_route = routes.filter(id=route_id).first()

            reservations = qs
        except ValueError:
            pass

    context = {
        "routes": routes,
        "reservations": reservations,
        "selected_date": selected_date,
        "selected_route": selected_route,
        "date_str": date_str,
        "route_id": route_id,
    }

    return render(
        request,
        "inventory/run_sheet.html",
        add_role_context(request, context),
    )


# ---------------------------
# Utilities
# ---------------------------

def get_next_code(request):
    category_id = request.GET.get("category_id")

    if not category_id:
        return JsonResponse({"code": ""})

    try:
        category = Category.objects.get(id=category_id)
    except Category.DoesNotExist:
        return JsonResponse({"code": ""})

    prefix = "UOS"
    cat_code = category.code.upper() if category.code else "XX"

    last_item = Item.objects.filter(
        category=category
    ).order_by("-code").first()

    if last_item and last_item.code:
        match = re.search(r"(\d+)$", last_item.code)
        last_number = int(match.group(1)) if match else 0
    else:
        last_number = 0

    next_number = str(last_number + 1).zfill(5)

    return JsonResponse({
        "code": f"{prefix}-{cat_code}{next_number}"
    })