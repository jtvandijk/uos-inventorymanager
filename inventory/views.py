from django.shortcuts import redirect, get_object_or_404, render
from django.http import JsonResponse, HttpResponseRedirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.contrib import messages

from django.contrib.auth.models import User

from .models import ActivityLog, Category, SizeOption, Item, Reservation, Route, SpecialRequest, UserProfile
from .forms import ItemForm, ItemEditForm, ReservationForm, SpecialRequestForm, SignUpForm

import re


# ---------------------------
# Permissions & Context
# ---------------------------

def is_admin(user):
    return user.groups.filter(name="Admin").exists()


def add_role_context(request, context):
    admin = is_admin(request.user)
    context["is_admin"] = admin
    if admin:
        context["pending_count"] = User.objects.filter(is_active=False).count()
    return context


def _log(user, action, item=None, item_code="", person="", route=None, detail=""):
    ActivityLog.objects.create(
        user=user,
        action=action,
        item_code=item.code if item else item_code,
        person=person,
        route_name=route.name if route else "",
        detail=detail,
    )


# ---------------------------
# Special Request Helpers
# ---------------------------

def _next_walk_day(weekday):
    from datetime import date, timedelta
    today = date.today()
    days = (weekday - today.weekday()) % 7 or 7
    return today + timedelta(days=days)


def _try_auto_assign_special(item, by_user=None, note_reason=None):
    if not item.category.is_special:
        return None
    req = SpecialRequest.objects.filter(
        category=item.category,
        status="active",
    ).order_by("requested_at").first()
    if not req:
        return None
    if note_reason:
        note = f"Re-assigned following {note_reason} (originally requested {req.requested_at.date()})."
    else:
        note = f"Special request auto-assigned (originally requested {req.requested_at.date()})."
    res = Reservation(
        item=item,
        person=req.person,
        route=req.route,
        reserved_for_date=_next_walk_day(req.requested_at.weekday()),
        notes=note,
        reserved_by=by_user or req.requested_by,
    )
    res.save()
    SpecialRequest.objects.filter(pk=req.pk).update(
        status="fulfilled",
        fulfilled_at=timezone.now(),
        fulfilled_by_item=item,
    )
    return req


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

    if status == "special":
        items = items.filter(category__is_special=True).exclude(status="given")
    elif status:
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
    elided_range = list(paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1))

    context = {
        "page_obj": page_obj,
        "elided_range": elided_range,
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

    replacement_available = False
    if reservation:
        replacement_available = Item.objects.filter(
            category=item.category,
            gender=item.gender,
            size=item.size,
            status="available",
        ).exclude(id=item.id).exists()

    context = {
        "item": item,
        "reservation": reservation,
        "replacement_available": replacement_available,
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

            _log(request.user, "reserve", item=item, person=reservation.person, route=reservation.route)
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

    item = reservation.item
    next_url = request.GET.get("next") or request.POST.get("next") or "/inventory/"

    if request.method == "POST":
        form = ReservationForm(request.POST, instance=reservation)
        if form.is_valid():
            form.save()
            _log(request.user, "edit_reservation", item=item, person=reservation.person, route=reservation.route)
            messages.success(request, f"Reservation for {reservation.person} updated.")
            from django.urls import reverse
            from urllib.parse import quote
            return redirect(f"{reverse('view_item', args=[item.id])}?next={quote(next_url, safe='')}")
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
    item = get_object_or_404(Item.objects.select_related("category"), id=item_id)

    reservation = Reservation.objects.filter(
        item=item,
        status__in=["reserved", "packed"],
    ).first()

    if reservation and (
        reservation.reserved_by == request.user or is_admin(request.user)
    ):
        _log_person = reservation.person
        _log_route = reservation.route
        _log_code = item.code
        if item.category.is_special:
            sr = SpecialRequest.objects.filter(fulfilled_by_item=item, status="fulfilled").first()
            if sr:
                SpecialRequest.objects.filter(pk=sr.pk).update(
                    status="lapsed",
                    lapsed_at=timezone.now(),
                )
        reservation.delete()  # sets item → available via model override
        if item.category.is_special:
            _try_auto_assign_special(item, by_user=request.user, note_reason="cancellation")
        _log(request.user, "cancel_reservation", item_code=_log_code, person=_log_person, route=_log_route)
        messages.success(request, "Reservation cancelled.")

    return redirect(request.GET.get("next") or "/inventory/")


@login_required
def pack_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    next_url = request.GET.get("next") or request.POST.get("next") or "/inventory/"

    reservation = Reservation.objects.filter(
        item=item,
        status__in=["reserved", "packed"],
    ).first()

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if reservation:
        new_status = "packed" if reservation.status == "reserved" else "reserved"
        reservation.status = new_status
        reservation.save()
        if not is_ajax:
            messages.success(request, f"Item marked as {'packed' if new_status == 'packed' else 'unpacked'}.")

    if is_ajax:
        return JsonResponse({"status": reservation.status if reservation else ""})

    return redirect(next_url)


@login_required
def collect_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)

    if item.status in ("reserved", "packed"):
        reservation = Reservation.objects.filter(
            item=item, status__in=["reserved", "packed"]
        ).select_related("route").first()

        # Use QuerySet.update() to bypass Reservation.delete() cascade (would set item→available)
        # Keeping the reservation preserves person's name for the Collected view
        Reservation.objects.filter(
            item=item,
            status__in=["reserved", "packed"],
        ).update(status="given")

        item.status = "given"
        item.given_by = request.user
        item.given_at = timezone.now()
        item.updated_at = timezone.now()
        item.save()

        _log(request.user, "collect", item=item,
             person=reservation.person if reservation else "",
             route=reservation.route if reservation else None)
        messages.success(request, f"Item {item.code} collected.")

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
            gender = "unisex" if category.is_special else form.cleaned_data["gender"]
            size = "" if category.is_special else form.cleaned_data.get("size", "")
            device_code = form.cleaned_data.get("device_code", "")
            sim_number = form.cleaned_data.get("sim_number", "")

            created_codes = []
            assigned_to = []
            for _ in range(quantity):
                item = Item(
                    category=category,
                    gender=gender,
                    size=size,
                    device_code=device_code,
                    sim_number=sim_number,
                    created_by=request.user,
                    updated_at=timezone.now(),
                )
                item.save()
                created_codes.append(item.code)
                req = _try_auto_assign_special(item, by_user=request.user)
                if req:
                    assigned_to.append((item.code, req.person))

            if assigned_to:
                names = ", ".join(f"{code} → {person}" for code, person in assigned_to)
                messages.success(request, f"Auto-assigned from special request queue: {names}")

            from django.urls import reverse
            codes_param = ",".join(created_codes)
            return redirect(reverse("add_item_confirm") + f"?codes={codes_param}")
    else:
        form = ItemForm()

    import json
    categories_data = {
        str(cat.id): {"is_special": cat.is_special, "extra_field": cat.extra_field}
        for cat in Category.objects.all()
    }
    context = {"form": form, "categories_data_json": json.dumps(categories_data)}

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


@login_required
def reassign_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    next_url = request.GET.get("next") or "/inventory/"

    reservation = Reservation.objects.filter(
        item=item,
        status__in=["reserved", "packed"],
    ).select_related("route").first()

    if not reservation:
        return redirect(next_url)

    replacement = Item.objects.filter(
        category=item.category,
        gender=item.gender,
        size=item.size,
        status="available",
    ).exclude(id=item.id).first()

    person = reservation.person
    original_date = reservation.reserved_for_date

    if replacement:
        reassign_note = f"Re-assigned from {item.code} on {timezone.now().date()}."
        new_notes = (reservation.notes + "\n" + reassign_note) if reservation.notes else reassign_note

        new_res = Reservation(
            item=replacement,
            person=reservation.person,
            reserved_for_date=reservation.reserved_for_date,
            route=reservation.route,
            notes=new_notes,
            reserved_by=reservation.reserved_by,
        )
        new_res.save()

        # Bypass model.delete() cascade (would set item→available); we want item→given
        Reservation.objects.filter(pk=reservation.pk).delete()

        item.status = "given"
        item.given_by = request.user
        item.given_at = timezone.now()
        item.updated_at = timezone.now()
        item.save()

        _log(request.user, "reassign", item=item, person=person, route=reservation.route,
             detail=f"Replaced by {replacement.code}")
        messages.success(
            request,
            f"Re-assigned to {replacement.code}. {person}'s reservation moved with collection date {original_date}.",
        )
        from django.urls import reverse
        from urllib.parse import quote
        return redirect(f"{reverse('view_item', args=[replacement.id])}?next={quote(next_url, safe='')}")

    else:
        item.status = "given"
        item.given_by = request.user
        item.given_at = timezone.now()
        item.updated_at = timezone.now()
        item.save()

        sr = SpecialRequest.objects.filter(fulfilled_by_item=item, status="fulfilled").first()
        if sr:
            # Revert to active at original queue position — person is still being served via SR
            SpecialRequest.objects.filter(pk=sr.pk).update(
                status="active",
                fulfilled_at=None,
                fulfilled_by_item=None,
            )
            # Remove reservation — do NOT log as missed, person is back in queue
            # Use queryset delete to bypass model.delete() override (item already "given")
            Reservation.objects.filter(pk=reservation.pk).delete()

            # Immediately try to re-assign if another item of this category is available
            other_item = Item.objects.filter(category=item.category, status="available").first()
            if other_item:
                _try_auto_assign_special(other_item, by_user=request.user, note_reason="item given on walk")
                messages.warning(
                    request,
                    f"{item.category.name} given on walk. {person}'s special request immediately re-assigned to {other_item.code}.",
                )
            else:
                messages.warning(
                    request,
                    f"{item.category.name} given on walk. {person}'s special request returned to the queue — will be assigned when one becomes available.",
                )
            _log(request.user, "reassign", item=item, person=person, route=reservation.route,
                 detail=f"SR returned to queue — {item.category.name}")
        else:
            # Regular item: item is definitively gone, log immediately as missed
            miss_note = f"Item {item.code} given to another person on {timezone.now().date()} — no replacement available."
            new_notes = (reservation.notes + "\n" + miss_note) if reservation.notes else miss_note
            Reservation.objects.filter(pk=reservation.pk).update(
                status="missed",
                miss_reason="no_replacement",
                missed_at=timezone.now(),
                notes=new_notes,
            )
            _log(request.user, "reassign", item=item, person=person, route=reservation.route,
                 detail="No replacement available")
            messages.warning(
                request,
                f"No replacement in stock. {person}'s reservation has been logged in Missed Collections.",
            )

        return redirect(next_url)


@login_required
def missed_collections_view(request):
    if not is_admin(request.user):
        return redirect("volunteer")

    sort = request.GET.get("sort", "-missed_at")
    reason_filter = request.GET.get("reason", "")
    allowed_sorts = {
        "person": "person", "-person": "-person",
        "code": "item__code", "-code": "-item__code",
        "category": "item__category__name", "-category": "-item__category__name",
        "gender": "item__gender", "-gender": "-item__gender",
        "size": "item__size", "-size": "-item__size",
        "date": "reserved_for_date", "-date": "-reserved_for_date",
        "route": "route__name", "-route": "-route__name",
        "reason": "miss_reason", "-reason": "-miss_reason",
        "missed_at": "missed_at", "-missed_at": "-missed_at",
    }
    missed_qs = Reservation.objects.filter(status="missed").select_related("item", "item__category", "route")
    if reason_filter == "lapsed":
        missed_qs = missed_qs.filter(miss_reason="lapsed")
    elif reason_filter == "no_replacement":
        missed_qs = missed_qs.filter(miss_reason="no_replacement")
    missed_qs = missed_qs.order_by(allowed_sorts.get(sort, "-missed_at"))

    paginator = Paginator(missed_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    elided_range = list(paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1))

    context = {"page_obj": page_obj, "elided_range": elided_range, "sort": sort, "reason_filter": reason_filter}
    return render(request, "inventory/missed_collections.html", add_role_context(request, context))


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

    paginator = Paginator(items.order_by("code"), 3)
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
        status="reserved",
    ).exclude(item__fulfilled_special_request__status="fulfilled")

    res_page_obj = Paginator(my_res.order_by("-id"), 3).get_page(
        request.GET.get("res_page")
    )

    # Fulfilled SRs whose collection date is today — shown so volunteers can collect
    sr_fulfilled_qs = SpecialRequest.objects.filter(
        status="fulfilled",
        fulfilled_by_item__reservation__reserved_for_date=timezone.localdate(),
        fulfilled_by_item__reservation__status__in=["reserved", "packed"],
    ).select_related("category", "route", "requested_by", "fulfilled_by_item").order_by("fulfilled_at")

    sr_search = request.GET.get("q", "")
    sr_qs = SpecialRequest.objects.filter(
        status="active",
    ).select_related("category", "route", "requested_by").order_by("requested_at")
    if sr_search:
        sr_qs = sr_qs.filter(
            Q(person__icontains=sr_search) |
            Q(category__name__icontains=sr_search) |
            Q(route__name__icontains=sr_search)
        )
    sr_paginator = Paginator(sr_qs, 3)
    sr_page_obj = sr_paginator.get_page(request.GET.get("sr_page"))
    context = {
        "page_obj": page_obj,
        "my_reservations": res_page_obj,
        "res_page_obj": res_page_obj,
        "search": search,
        "status_filter": status_filter,
        "sr_page_obj": sr_page_obj,
        "sr_search": sr_search,
        "sr_fulfilled": sr_fulfilled_qs,
    }

    return render(
        request,
        "inventory/volunteer.html",
        add_role_context(request, context),
    )


# ---------------------------
# Special Requests
# ---------------------------

@login_required
def create_special_request(request):
    next_url = request.GET.get("next") or request.POST.get("next") or "/inventory/volunteer/"

    if request.method == "POST":
        form = SpecialRequestForm(request.POST)
        if form.is_valid():
            sr = form.save(commit=False)
            sr.requested_by = request.user
            sr.save()
            _log(request.user, "new_sr", person=sr.person, route=sr.route, detail=sr.category.name)
            available_item = Item.objects.filter(category=sr.category, status="available").first()
            if available_item:
                assigned_req = _try_auto_assign_special(available_item, by_user=request.user)
                if assigned_req:
                    messages.success(
                        request,
                        f"Stock found — {assigned_req.person}'s request for {sr.category.name} "
                        f"was immediately assigned to {available_item.code}."
                    )
                else:
                    messages.success(request, f"Special request for {sr.person} ({sr.category.name}) added to the queue.")
            else:
                messages.success(request, f"Special request for {sr.person} ({sr.category.name}) added to the queue.")
            return redirect(next_url)
    else:
        form = SpecialRequestForm()

    context = {"form": form, "next": next_url}
    return render(request, "inventory/special_request.html", add_role_context(request, context))


@login_required
def admin_special_requests_view(request):
    if not is_admin(request.user):
        return redirect("volunteer")

    status_filter = request.GET.get("status", "")
    sort = request.GET.get("sort", "-requested_at")
    allowed_sorts = {
        "person": "person", "-person": "-person",
        "category": "category__name", "-category": "-category__name",
        "route": "route__name", "-route": "-route__name",
        "requested_at": "requested_at", "-requested_at": "-requested_at",
        "last_confirmed_at": "last_confirmed_at", "-last_confirmed_at": "-last_confirmed_at",
        "status": "status", "-status": "-status",
        "item": "fulfilled_by_item__code", "-item": "-fulfilled_by_item__code",
    }

    qs = SpecialRequest.objects.select_related(
        "category", "route", "requested_by", "fulfilled_by_item"
    )
    if status_filter == "all":
        pass
    elif status_filter == "collected":
        qs = qs.filter(status="fulfilled", fulfilled_by_item__status="given")
    elif status_filter == "lapsed":
        qs = qs.filter(status="lapsed")
    elif status_filter == "active":
        qs = qs.filter(status="active")
    else:
        # Default: active + assigned (fulfilled but item not yet given)
        qs = qs.filter(
            Q(status="active") |
            Q(status="fulfilled", fulfilled_by_item__status__in=["reserved", "packed"])
        )

    qs = qs.order_by(allowed_sorts.get(sort, "-requested_at"))

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    elided_range = list(paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1))

    context = {"page_obj": page_obj, "elided_range": elided_range, "status_filter": status_filter, "sort": sort}
    return render(request, "inventory/admin_special_requests.html", add_role_context(request, context))


@login_required
def confirm_special_request(request, sr_id):
    sr = get_object_or_404(SpecialRequest, id=sr_id, status="active")
    next_url = request.POST.get("next") or request.GET.get("next") or "/inventory/volunteer/"
    SpecialRequest.objects.filter(pk=sr.pk).update(last_confirmed_at=timezone.now())
    _log(request.user, "confirm_sr", person=sr.person, route=sr.route, detail=sr.category.name)
    messages.success(request, f"Confirmed {sr.person}'s request is still active. 4-week clock reset.")
    return redirect(next_url)


@login_required
def cancel_special_request(request, sr_id):
    sr = get_object_or_404(SpecialRequest, id=sr_id, status="active")
    next_url = request.POST.get("next") or request.GET.get("next") or "/inventory/volunteer/"
    if sr.requested_by != request.user and not is_admin(request.user):
        return redirect(next_url)
    SpecialRequest.objects.filter(pk=sr.pk).update(
        status="lapsed",
        lapsed_at=timezone.now(),
    )
    _log(request.user, "cancel_sr", person=sr.person, route=sr.route, detail=sr.category.name)
    messages.success(request, f"Special request for {sr.person} ({sr.category.name}) cancelled.")
    return redirect(next_url)


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


# ---------------------------
# User sign-up & approval
# ---------------------------

def signup_view(request):
    if request.user.is_authenticated:
        return redirect("inventory" if is_admin(request.user) else "volunteer")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = form.cleaned_data.get("first_name", "")
            user.last_name = form.cleaned_data.get("last_name", "")
            user.email = form.cleaned_data.get("email", "")
            user.is_active = False
            user.save()
            UserProfile.objects.create(user=user, phone=form.cleaned_data.get("phone", ""))
            return render(request, "inventory/signup.html", {"success": True})
    else:
        form = SignUpForm()

    return render(request, "inventory/signup.html", {"form": form})


@login_required
def users_view(request):
    if not is_admin(request.user):
        return redirect("volunteer")

    users_qs = User.objects.prefetch_related("groups").order_by("username")
    paginator = Paginator(users_qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))
    elided_range = list(paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1))

    phone_map = {p.user_id: p.phone for p in UserProfile.objects.filter(user__in=page_obj.object_list)}
    for u in page_obj.object_list:
        u.is_admin_flag = u.groups.filter(name="Admin").exists()
        u.phone_num = phone_map.get(u.pk, "")

    return render(request, "inventory/users.html", add_role_context(request, {
        "page_obj": page_obj,
        "elided_range": elided_range,
    }))


@login_required
def approve_user(request, user_id):
    if not is_admin(request.user) or request.method != "POST":
        return redirect("users")
    User.objects.filter(pk=user_id, is_active=False).update(is_active=True)
    return redirect("users")


@login_required
def reject_user(request, user_id):
    if not is_admin(request.user) or request.method != "POST":
        return redirect("users")
    User.objects.filter(pk=user_id, is_active=False, is_superuser=False).delete()
    return redirect("users")


@login_required
def delete_user(request, user_id):
    if not is_admin(request.user) or request.method != "POST":
        return redirect("users")
    User.objects.filter(pk=user_id, is_superuser=False).exclude(pk=request.user.pk).delete()
    return redirect("users")


# ---------------------------
# Activity Log
# ---------------------------

@login_required
def activity_log_view(request):
    if not is_admin(request.user):
        return redirect("volunteer")

    logs = ActivityLog.objects.select_related("user").all()
    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    elided_range = list(paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1))

    return render(request, "inventory/activity_log.html", add_role_context(request, {
        "page_obj": page_obj,
        "elided_range": elided_range,
    }))