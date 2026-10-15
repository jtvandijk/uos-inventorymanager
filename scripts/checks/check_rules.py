"""One check per business rule in CLAUDE.md. Add a block here when a new rule or bug comes up."""
from datetime import date, timedelta

from inventory.models import Item, Reservation, SizeOption, SpecialRequest

from common import (Results, age_reservations, category, client, fresh, in_days, reset_stock, route,
                    run_daily_jobs, user)


def run():
    R = Results("Rules")
    admin, vol = user("chk_admin", admin=True), user("chk_vol")
    A, V = client(admin), client(vol)
    coat, bag = category("Coat"), category("Sleeping Bag")

    def add(cat, n=1, gender="male", size="L"):
        before = set(Item.objects.values_list("id", flat=True))
        data = {"category": cat.id, "gender": gender, "size": size, "quantity": n}
        if cat.is_special:
            data.update(gender="unisex", size="")
        A.post("/inventory/add/", data)
        return list(Item.objects.exclude(id__in=before).order_by("id"))

    def reserve(item, person, days=7, c=V):
        c.post(f"/inventory/reserve/{item.id}/", {
            "person": person, "route": route().id, "notes": "", "reserved_for_date": in_days(days)})

    def new_sr(person, c=V):
        c.post("/inventory/special-request/new/", {
            "person": person, "category": bag.id, "route": route().id, "notes": ""})
        return SpecialRequest.objects.filter(person=person).latest("id")

    # Sizes
    R.ok("sizes: clothing XS–XXXL", list(SizeOption.objects.filter(size_type="clothing").order_by("id").values_list("label", flat=True))
         == ["XS", "S", "M", "L", "XL", "XXL", "XXXL"])
    R.ok("sizes: trousers W28–W42 every inch", list(SizeOption.objects.filter(size_type="trousers").order_by("id").values_list("label", flat=True))
         == [f"W{w}" for w in range(28, 43)])
    R.ok("sizes: shoes UK 3–UK 13", list(SizeOption.objects.filter(size_type="shoes").order_by("id").values_list("label", flat=True))
         == [f"UK {s}" for s in range(3, 14)])

    # Two-miss lapse
    reset_stock()
    [c1] = add(coat)
    reserve(c1, "Ann")
    age_reservations(8); run_daily_jobs()
    r = Reservation.objects.get(item=c1)
    R.ok("lapse: first miss extends 7 days, same weekday",
         r.status == "reserved" and r.auto_extended and r.reserved_for_date == date.today() + timedelta(days=6), r.reserved_for_date)
    age_reservations(7); run_daily_jobs()
    r = fresh(r)
    R.ok("lapse: second miss -> missed/lapsed, item back to stock",
         r.status == "missed" and r.miss_reason == "lapsed" and fresh(c1).status == "available")
    reserve(c1, "Bob")
    R.ok("lapse: re-reserving keeps the missed record", Reservation.objects.filter(item=c1, status="missed").count() == 1)

    reset_stock()
    [c1] = add(coat)
    reserve(c1, "Ann")
    age_reservations(60); run_daily_jobs()
    r = Reservation.objects.get(item=c1)
    R.ok("lapse: long overdue -> next same-weekday walk from today",
         r.status == "reserved" and 0 <= (r.reserved_for_date - date.today()).days < 7, r.reserved_for_date)
    run_daily_jobs()
    R.ok("lapse: ...and not released the next day", fresh(r).status == "reserved")

    reset_stock()
    [c1] = add(coat)
    reserve(c1, "Ann")
    A.post(f"/inventory/pack/{c1.id}/")
    R.ok("pack: sets packed", fresh(c1).status == "packed")
    age_reservations(8); run_daily_jobs(); age_reservations(7); run_daily_jobs()
    R.ok("lapse: packed items lapse too", fresh(c1).status == "available")

    # Special request queue
    reset_stock()
    s1, s2 = new_sr("First"), new_sr("Second")
    [b1] = add(bag)
    R.ok("queue: new item goes to oldest request", fresh(s1).status == "fulfilled" and fresh(s1).fulfilled_by_item_id == b1.id)
    R.ok("queue: second still waiting", fresh(s2).status == "active")
    R.ok("queue: reservation belongs to the volunteer who filed the request",
         Reservation.objects.get(item=b1, status="reserved").reserved_by == vol)
    V.post(f"/inventory/cancel/{b1.id}/")
    R.ok("cancel special: request closed", fresh(s1).status == "lapsed")
    R.ok("cancel special: next in queue gets the item", fresh(s2).fulfilled_by_item_id == b1.id)

    reset_stock()
    s1, s2 = new_sr("First"), new_sr("Second")
    [b1] = add(bag)
    age_reservations(14); run_daily_jobs(); age_reservations(14); run_daily_jobs()
    R.ok("lapse special: first request lapsed", fresh(s1).status == "lapsed")
    R.ok("lapse special: item goes to second", fresh(s2).fulfilled_by_item_id == b1.id)
    R.ok("lapse special: only one request on the item",
         SpecialRequest.objects.filter(fulfilled_by_item=b1, status="fulfilled").count() == 1)

    # Re-assign
    reset_stock()
    c1, c2 = add(coat, 2)
    reserve(c1, "Ann")
    V.post(f"/inventory/item/{c1.id}/reassign/")
    R.ok("reassign: moves to identical spare",
         fresh(c1).status == "given" and Reservation.objects.filter(item=c2, person="Ann", status="reserved").exists())

    reset_stock()
    [c1] = add(coat)
    reserve(c1, "Ann")
    V.post(f"/inventory/item/{c1.id}/reassign/")
    r = Reservation.objects.get(item=c1)
    R.ok("reassign: no spare -> missed 'no replacement'", r.status == "missed" and r.miss_reason == "no_replacement")

    reset_stock()
    s1 = new_sr("First")
    [b1] = add(bag)
    new_sr("Second")
    V.post(f"/inventory/item/{b1.id}/reassign/")
    R.ok("reassign special, no spare: request back in queue", fresh(s1).status == "active" and fresh(s1).fulfilled_by_item_id is None)
    [b2] = add(bag)
    R.ok("reassign special: keeps queue position", fresh(s1).fulfilled_by_item_id == b2.id)

    reset_stock()
    s1 = new_sr("First")
    [b1], [b2] = add(bag), add(bag)
    V.post(f"/inventory/item/{b1.id}/reassign/")
    R.ok("reassign special with spare: request follows the spare", fresh(s1).fulfilled_by_item_id == b2.id)

    # Delete, edit, collect, pack all, permissions
    reset_stock()
    s1 = new_sr("First")
    [b1] = add(bag)
    A.post(f"/inventory/delete/{b1.id}/")
    R.ok("delete assigned special item: request back in queue", fresh(s1).status == "active")

    reset_stock()
    s1 = new_sr("First")
    r = V.post(f"/inventory/special-request/{s1.id}/edit/", {"person": "First Edited", "route": route().id, "notes": ""})
    R.ok("edit special request saves", r.status_code == 302 and fresh(s1).person == "First Edited", r.status_code)

    reset_stock()
    [c1] = add(coat)
    reserve(c1, "Ann")
    V.post(f"/inventory/collect/{c1.id}/")
    R.ok("collect: given, name kept", fresh(c1).status == "given"
         and Reservation.objects.filter(item=c1, status="given", person="Ann").exists())

    reset_stock()
    items = add(coat, 3)
    for i, it in enumerate(items):
        reserve(it, f"P{i}", days=3)
    A.post("/inventory/pack-all/", {"date": in_days(3), "route_id": "", "action": "pack"})
    R.ok("pack all", all(fresh(i).status == "packed" for i in items))
    A.post("/inventory/pack-all/", {"date": in_days(3), "route_id": "", "action": "unpack"})
    R.ok("unpack all", all(fresh(i).status == "reserved" for i in items))

    reset_stock()
    [c1] = add(coat)
    reserve(c1, "Ann", c=A)
    V.post(f"/inventory/cancel/{c1.id}/")
    R.ok("volunteer can't cancel someone else's reservation", fresh(c1).status == "reserved")

    reset_stock()
    [c1] = add(coat)
    reserve(c1, "Ann")
    A.post(f"/inventory/pack/{c1.id}/")
    r = Reservation.objects.get(item=c1)
    V.post(f"/inventory/reservation/{r.id}/edit/", {"person": "Ann B", "route": route().id, "notes": "",
                                                    "reserved_for_date": in_days(2)})
    R.ok("editing a packed reservation keeps it packed", fresh(r).status == "packed" and fresh(r).person == "Ann B")

    # Volunteer Reserved tab: route chips
    from inventory.models import Route
    reset_stock()
    c1, c2 = add(coat, 2)
    r1, r2 = Route.objects.order_by("id")[:2]
    for it, rt, who in [(c1, r1, "Ann"), (c2, r2, "Bob")]:
        V.post(f"/inventory/reserve/{it.id}/", {"person": who, "route": rt.id, "notes": "", "reserved_for_date": in_days(7)})
    h = V.get("/inventory/volunteer/", {"status": "reserved"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest").json()["html"]
    R.ok("route chips: one chip per route with reservations", h.count("setChip('route'") == 2)
    h = V.get("/inventory/volunteer/", {"status": "reserved", "route": r1.id}, HTTP_X_REQUESTED_WITH="XMLHttpRequest").json()["html"]
    R.ok("route chips: filters to that route", c1.code in h and c2.code not in h)
    h = V.get("/inventory/volunteer/", {"status": "available"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest").json()["html"]
    R.ok("route chips: not shown on the Inventory tab", "setChip('route'" not in h)

    return R
