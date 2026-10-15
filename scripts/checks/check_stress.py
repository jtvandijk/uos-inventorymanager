"""Random actions by several users, checking the data stays consistent after every step."""
import collections
import random
import traceback
from datetime import date, timedelta

from django.test import Client

from inventory.models import Category, Item, Reservation, Route, SizeOption, SpecialRequest

from common import Results, run_daily_jobs, user

NAMES = ["Jonny S", "Mary K", "Abdi H", "Tom W", "Lena P", "Kofi A", "Sam R", "Ewa M", "Dave L", "Priya N"]


def run(seeds=(1, 2, 3), steps=500):
    R = Results(f"Stress ({len(seeds)} runs x {steps} random actions)")
    for seed in seeds:
        errors, violations = _run_one(seed, steps)
        R.ok(f"seed {seed}: no server errors", not errors, "; ".join(errors[:3]))
        R.ok(f"seed {seed}: data stays consistent", not violations,
             "; ".join(f"{k} (x{n}, first: {ex})" for k, (n, ex) in list(violations.items())[:3]))
    return R


def _run_one(seed, steps):
    rng = random.Random(seed)
    admin = user("chk_stress_admin", admin=True)
    vols = [user(f"chk_stress_vol{i}") for i in range(3)]
    clients = {}
    for u in [admin] + vols:
        c = Client(raise_request_exception=True)
        c.force_login(u)
        clients[u.pk] = c
    routes = list(Route.objects.all())
    regular = list(Category.objects.filter(is_special=False))
    special = list(Category.objects.filter(is_special=True))
    sizes = {st: list(SizeOption.objects.filter(size_type=st).values_list("value", flat=True))
             for st in ["clothing", "trousers", "shoes"]}

    def anyone():
        return rng.choice([admin] + vols)

    def call(u, method, url, data=None, **extra):
        resp = getattr(clients[u.pk], method)(url, data or {}, **extra)
        if resp.status_code >= 500:
            raise RuntimeError(f"{method.upper()} {url} -> {resp.status_code}")

    def rand_date():
        return (date.today() + timedelta(days=rng.randint(-10, 14))).isoformat()

    def open_res():
        return list(Reservation.objects.filter(status__in=["reserved", "packed"]))

    def owner_or_admin(u):
        return u if (u and u.pk in clients and rng.random() < .7) else admin

    def add_regular():
        cat = rng.choice(regular)
        call(admin, "post", "/inventory/add/", {
            "category": cat.id, "gender": rng.choice(["male", "female", "unisex"]),
            "size": rng.choice(sizes.get(cat.size_type) or [""]), "quantity": rng.randint(1, 3)})

    def add_special():
        cat = rng.choice(special)
        data = {"category": cat.id, "gender": "unisex", "size": "", "quantity": 1}
        if cat.extra_field == "device_code":
            data["device_code"] = "Test phone"
        if cat.extra_field == "sim_number":
            data["sim_number"] = "07700 900123"
        call(admin, "post", "/inventory/add/", data)

    def reserve():
        items = list(Item.objects.filter(status="available")[:200])
        if items:
            call(anyone(), "post", f"/inventory/reserve/{rng.choice(items).id}/", {
                "person": rng.choice(NAMES), "reserved_for_date": rand_date(), "route": rng.choice(routes).id, "notes": ""})

    def edit_res():
        rs = open_res()
        if rs:
            r = rng.choice(rs)
            call(anyone(), "post", f"/inventory/reservation/{r.id}/edit/", {
                "person": r.person, "reserved_for_date": rand_date(), "route": r.route_id or routes[0].id, "notes": "edited"})

    def item_action(path, who=None):
        def act():
            rs = open_res()
            if rs:
                r = rng.choice(rs)
                call(who(r) if who else anyone(), "post", path.format(r.item_id))
        return act

    def pack_all():
        rs = open_res()
        if rs:
            r = rng.choice(rs)
            call(admin, "post", "/inventory/pack-all/", {
                "date": r.reserved_for_date.isoformat(), "route_id": rng.choice(["", r.route_id or ""]),
                "action": rng.choice(["pack", "unpack"])})

    def new_sr():
        call(anyone(), "post", "/inventory/special-request/new/", {
            "person": rng.choice(NAMES), "category": rng.choice(special).id, "route": rng.choice(routes).id, "notes": ""})

    def sr_action(path, data=None):
        def act():
            srs = list(SpecialRequest.objects.filter(status="active"))
            if srs:
                s = rng.choice(srs)
                payload = data(s) if data else None
                call(owner_or_admin(s.requested_by), "post", path.format(s.id), payload)
        return act

    def edit_item():
        items = list(Item.objects.exclude(status="given").select_related("category")[:300])
        if items:
            it = rng.choice(items)
            call(admin, "post", f"/inventory/item/{it.id}/edit/", {
                "category": it.category_id, "gender": it.gender,
                "size": rng.choice(sizes.get(it.category.size_type) or [""]),
                "device_code": it.device_code or "", "sim_number": it.sim_number or ""})

    def delete_item():
        items = list(Item.objects.all()[:500])
        if items:
            call(admin, "post", f"/inventory/delete/{rng.choice(items).id}/")

    def days_pass():
        n = rng.choice([1, 3, 7, 10])
        for r in Reservation.objects.filter(status__in=["reserved", "packed"]):
            Reservation.objects.filter(pk=r.pk).update(reserved_for_date=r.reserved_for_date - timedelta(days=n))
        for s in SpecialRequest.objects.all():
            SpecialRequest.objects.filter(pk=s.pk).update(
                last_confirmed_at=s.last_confirmed_at - timedelta(days=n), requested_at=s.requested_at - timedelta(days=n))
        run_daily_jobs()

    actions = [
        (add_regular, 6), (add_special, 5), (reserve, 14), (edit_res, 4),
        (item_action("/inventory/cancel/{}/", who=lambda r: owner_or_admin(r.reserved_by)), 5),
        (item_action("/inventory/pack/{}/", who=lambda r: admin), 8), (pack_all, 2),
        (item_action("/inventory/collect/{}/"), 7), (item_action("/inventory/item/{}/reassign/"), 5),
        (new_sr, 6), (sr_action("/inventory/special-request/{}/confirm/"), 3),
        (sr_action("/inventory/special-request/{}/cancel/"), 2),
        (sr_action("/inventory/special-request/{}/edit/",
                   lambda s: {"person": s.person, "route": s.route_id or routes[0].id, "notes": "edited"}), 2),
        (edit_item, 3), (delete_item, 1), (days_pass, 3),
    ]
    fns, weights = zip(*actions)

    errors, violations = [], {}
    for step in range(steps):
        try:
            rng.choices(fns, weights)[0]()
        except Exception:
            line = traceback.format_exc().strip().splitlines()[-1]
            if line not in errors:
                errors.append(line)
        for kind, example in _broken_rules(special):
            n, first = violations.get(kind, (0, f"step {step}: {example}"))
            violations[kind] = (n + 1, first)
        if step % 100 == 0:
            for url in ["/inventory/", "/inventory/overview/", "/inventory/missed/", "/inventory/special-requests/",
                        "/inventory/run-sheet/", "/inventory/activity/", "/inventory/volunteer/"]:
                try:
                    call(admin, "get", url)
                except Exception as e:
                    errors.append(f"{url}: {e}")
    return errors, violations


def _broken_rules(special_cats):
    """Yield (rule, example) for every consistency rule that doesn't hold right now."""
    open_by_item = collections.defaultdict(list)
    for r in Reservation.objects.filter(status__in=["reserved", "packed"]):
        open_by_item[r.item_id].append(r)
    fulfilled_by_item = collections.defaultdict(list)
    for s in SpecialRequest.objects.filter(status="fulfilled"):
        fulfilled_by_item[s.fulfilled_by_item_id].append(s)

    for it in Item.objects.all():
        act = open_by_item.get(it.id, [])
        if it.status in ("reserved", "packed"):
            if len(act) != 1:
                yield "reserved/packed item without exactly one open reservation", it.code
            elif act[0].status != it.status:
                yield "item status differs from its reservation", it.code
        elif act:
            yield "available/given item still has an open reservation", it.code
        if it.status == "given" and not it.given_at:
            yield "given item without given_at", it.code
        frs = fulfilled_by_item.get(it.id, [])
        if len(frs) > 1:
            yield "item linked to more than one fulfilled request", it.code
        if frs and it.status == "available":
            yield "fulfilled request points at an available item", it.code
        if frs and act and act[0].person != frs[0].person:
            yield "request person differs from reservation person", it.code
    if fulfilled_by_item.get(None):
        yield "fulfilled request with no item", fulfilled_by_item[None][0].person
    if SpecialRequest.objects.filter(status="active", fulfilled_by_item__isnull=False).exists():
        yield "active request still linked to an item", ""
    for cat in special_cats:
        if Item.objects.filter(category=cat, status="available").exists() and \
           SpecialRequest.objects.filter(category=cat, status="active").exists():
            yield "special item in stock while someone waits", cat.name
