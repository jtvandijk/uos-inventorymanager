# CLAUDE.md — Under One Sky Inventory Manager

## Project
Django inventory management app for Under One Sky, a London street outreach charity.
Manages clothing donations distributed across named outreach routes (Waterloo, Kings Cross, etc.).
Built and maintained by a solo volunteer. Keep solutions simple — no over-engineering.

## Stack
- Django 6, SQLite
- Bootstrap 5.3.3 (CDN), Bootstrap Icons 1.11.3 (CDN)
- Vanilla JS only — no build step, no npm
- Nginx + Gunicorn in production
- `stockmanager/settings_prod.py` for production overrides

## Django apps
- `inventory` — the only app; all models, views, forms, templates live here
- `stockmanager` — project settings/urls only

## Roles & permissions
- Two roles: **Admin** (Django group named exactly `"Admin"`) and **Volunteer** (any authenticated non-admin user)
- Permission check: `is_admin(user)` in `views.py` — checks `user.groups.filter(name="Admin")`
- Always pass `is_admin` to templates via `add_role_context(request, context)`
- Volunteers: reserve items, cancel/edit their own reservations, mark items collected, re-assign
- Admins: everything, including pack/unpack, add/edit/delete items, run sheet, missed collections

## Item workflow
`available` → `reserved` → `packed` → `given` (displayed as "Collected")

Status lives on both `Item.status` and `Reservation.status` — `Reservation.save()` cascades to `Item`.

## Item codes
Format: `UOS-{CATEGORY_CODE}{00001}` — auto-generated on `Item.save()` when code is blank.
Category codes are 2-character uppercase strings. Never let users edit item codes.

## Key patterns

**`next` parameter:** All action views accept a `?next=` param for redirect-after-action.
On `view_item`, actions redirect back to view_item itself (preserving the original `next` for the Back button):
```
href="{% url 'pack_item' item.id %}?next={{ item_url }}?next={{ next }}"
```

**AJAX detection:** Run sheet uses `XMLHttpRequest` header for pack toggle.
Check with `request.headers.get("x-requested-with") == "XMLHttpRequest"`.
Do NOT add Django messages inside AJAX-handled branches — they accumulate silently.

**Size options:** Populated via AJAX (`/inventory/get-sizes/?category_id=X`) on category change.
On edit forms, pre-populate sizes on page load and pre-select the current value.

**Flash messages:** `view_item.html` displays Django messages at the top of the card with 5s auto-dismiss.
Inventory list also shows messages. Other pages do not — don't assume messages show everywhere.

## Templates
- No base template — each page is standalone with its own `<head>`
- Bootstrap loaded from CDN on every page (not collected static)
- Favicon: `{% static 'favicon.ico' %}` — Under One Sky branded
- Logo: `{% static 'logo.png' %}` — transparent background PNG

## Reservation lapse system

**Management command:** `inventory/management/commands/process_lapses.py`
Run daily via cron: `python manage.py process_lapses`

**Two-pass logic (runs in order):**

Pass 1 — second miss (release to stock):
- Finds reservations where `auto_extended=True` and `reserved_for_date < today`
- Sets reservation `status="missed"`, `miss_reason="lapsed"`, `missed_at=now()`
- Releases item back to `status="available"`
- Uses `QuerySet.update()` throughout — never `reservation.save()` or `reservation.delete()`

Pass 2 — first miss (extend by 7 days):
- Finds reservations where `auto_extended=False` and `reserved_for_date < today` and status in `["reserved","packed"]`
- Pushes `reserved_for_date` forward 7 days, sets `auto_extended=True`, appends note
- Also uses `QuerySet.update()` to bypass `Reservation.save()` cascade

**Why `QuerySet.update()` not `save()`:**
`Reservation.save()` calls `full_clean()` and cascades status to `Item`. For lapse logic we need to bypass both — we handle item status ourselves, and "missed" is not a valid `clean()` state transition from "reserved".

**Why `QuerySet.delete()` not `model.delete()` in re-assign:**
`Reservation.model.delete()` sets `item.status = "available"` via signal/override. When re-assigning to a found replacement, we want `item.status = "given"`, so use `Reservation.objects.filter(pk=...).delete()` to bypass the cascade.

**Reservation model fields added for lapse:**
```python
auto_extended = models.BooleanField(default=False)
miss_reason = models.CharField(max_length=20, blank=True, default="",
    choices=[("lapsed","Lapsed"),("no_replacement","No replacement found")])
missed_at = models.DateTimeField(null=True, blank=True)
# status choices also include ("missed", "Missed")
```

**Clock icon:** `bi-clock-history` in orange (`#e67e22`) shown in inventory list and view_item when `reservation.auto_extended` is True.

## Re-assign feature

Volunteers and admins can re-assign a reservation when the item is given to a different person.

If a replacement item exists (same category, gender, size, status=available):
- Delete original reservation via `Reservation.objects.filter(pk=...).delete()` (bypasses cascade)
- Set `item.status = "given"`, `item.given_by = request.user`, `item.save()`
- Create new `Reservation` on the replacement item (same person, date, route, notes)

If no replacement available:
- `Reservation.objects.filter(pk=...).update(status="missed", miss_reason="no_replacement", missed_at=now())`
- Set `item.status = "given"`, `item.save()`

The `view_item` context pre-computes `replacement_available` (True/False) so the modal text is context-aware before the user submits.

## Missed collections

`/inventory/missed/` — admin-only, paginated (10/page), ordered by `-missed_at`.

Stores reservations with `status="missed"`. Two reasons:
- `"lapsed"` — two consecutive missed collections (via `process_lapses`)
- `"no_replacement"` — given to someone else but no matching stock found (via `reassign_item`)

Missed reservations stay linked to their original item in the DB. New reservations can be created for the same item without conflict — `Reservation.clean()` only checks `status="reserved"`.

## Test setup scripts

**`seed_categories.py`** — run once (or re-run safely, uses `get_or_create`):
```bash
python manage.py shell < seed_categories.py
```
Creates 16 categories with 2-char codes, UK size options (clothing XS–XXXL, trousers 28–42" waist, shoes UK 3–13), and 7 routes with exact brand colours.

**`seed_data.py`** — wipes items and reservations only (preserves users, categories, routes, sizes):
```bash
python manage.py shell < seed_data.py
```
Creates 50 items: ~88% available, ~8% reserved, ~2% packed, ~2% collected.

## Coding conventions
- No comments unless the WHY is non-obvious
- No over-engineering: don't add abstractions, error handling, or features beyond what's asked
- Validate at boundaries only (user input, external calls) — trust Django internals
- No backwards-compat shims for removed code — delete cleanly

## Production
- Server: Linode VPS, IP `178.79.153.239`
- Domain: `uos-inventory.duckdns.org` (DuckDNS + Let's Encrypt)
- `ALLOWED_HOSTS` needs bare hostname; `CSRF_TRUSTED_ORIGINS` needs scheme+hostname
- `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` — Nginx sets this header
- After template/static changes: `python manage.py collectstatic`
- Restart after code changes: `sudo systemctl restart gunicorn`
