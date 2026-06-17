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
- `resources` — standalone public volunteer resource hub (`/resources/`); no models, single view + hardcoded template. No login required.

## Roles & permissions
- Two roles: **Admin** (Django group named exactly `"Admin"`) and **Volunteer** (any authenticated non-admin user)
- Permission check: `is_admin(user)` in `views.py` — checks `user.groups.filter(name="Admin")`
- Always pass `is_admin` to templates via `add_role_context(request, context)`
- Volunteers: reserve items, cancel/edit their own reservations, mark items collected, re-assign, file/confirm/cancel special requests
- Admins: everything, including pack/unpack, add/edit/delete items, run sheet, missed collections, special requests admin log

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

**Why `collect_item` uses `QuerySet.update(status="given")` not `.delete()`:**
Keeping the reservation with `status="given"` preserves the person's name for the inventory Collected view. The "Reserved For" column in `inventory.html` checks `status in ["reserved","packed","given"]`. Using `QuerySet.update()` bypasses `Reservation.delete()` (which would reset item→available); item status is then set manually to "given".

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

If no replacement available — **two paths depending on item type:**

**Regular item:**
- Set `item.status = "given"`, `item.save()`
- Immediately mark reservation `status="missed", miss_reason="no_replacement", missed_at=now()` — item is definitively gone, no point waiting through lapse cycle
- Appears in Missed Collections with reason "No replacement"

**Special request item (category.is_special=True):**
- Set `item.status = "given"`, `item.save()`
- Find the SpecialRequest that was fulfilled by this item: `SpecialRequest.objects.filter(fulfilled_by_item=item, status="fulfilled")`
- Revert it to `status="active"`, `fulfilled_at=None`, `fulfilled_by_item=None` — back in queue at original position
- Delete the reservation via `Reservation.objects.filter(pk=...).delete()` (queryset delete bypasses cascade; item already "given")
- Do NOT log as missed — person is still being served via SR queue
- Immediately check for another available item of the same category; if found, call `_try_auto_assign_special(other_item, note_reason="item given on walk")` to re-assign without waiting for daily cron
- If no other item: SR stays active until one is added (`add_item` triggers auto-assign) or daily `process_special_lapses` Pass 2 fires

The `view_item` context pre-computes `replacement_available` (True/False) so the modal text is context-aware before the user submits.

## Missed collections

`/inventory/missed/` — admin-only, paginated (10/page), ordered by `-missed_at`.

Stores reservations with `status="missed"`. Reasons:
- `"lapsed"` — two consecutive missed collections (via `process_lapses`)
- `"no_replacement"` — regular item given to someone else on the walk with no matching replacement in stock (via `reassign_item`)

Missed reservations stay linked to their original item in the DB. New reservations can be created for the same item without conflict — `Reservation.clean()` only checks `status="reserved"`.

Notes on missed reservations are always system-generated (appended by `process_lapses` or `reassign_item`). No chat-icon is shown — the Reason badge and View → view_item are sufficient. Filter pills: Lapsed / No Replacement (no default; Clear appears when filter active).

## Cancel reservation

`cancel_reservation` calls `reservation.delete()` which sets `item.status = "available"` via the model override.

**For special items:** before deleting the reservation, the linked `SpecialRequest` (`fulfilled_by_item=item, status="fulfilled"`) is lapsed (`status="lapsed"`). After delete, `_try_auto_assign_special` fires immediately to give the item to the next person in queue. Cancelling is a deliberate volunteer action meaning the person no longer needs the item — the SR is done.

**For regular items:** just `reservation.delete()`. Item returns to available. No queue to re-assign to.

## Special request system

Handles items not normally in stock (Tent, Mobile Phone, SIM Card). Categories are flagged with `Category.is_special=True`.

**`SpecialRequest` model fields:**
```python
person = CharField(max_length=100)
route = ForeignKey(Route, null=True)
category = ForeignKey(Category, limit_choices_to={"is_special": True})
notes = TextField(blank=True)
status = CharField(choices=[("active","Active"),("fulfilled","Fulfilled"),("lapsed","Lapsed")])
requested_by = ForeignKey(User, null=True)
requested_at = DateTimeField(auto_now_add=True)
last_confirmed_at = DateTimeField(auto_now_add=True)  # reset by "Still Active"
fulfilled_by_item = ForeignKey(Item, null=True, blank=True, related_name="fulfilled_special_request")
fulfilled_at = DateTimeField(null=True, blank=True)
lapsed_at = DateTimeField(null=True, blank=True)
```

**Category extra fields:**
- `Category.extra_field` choices: `none` / `device_code` / `phone_number`
- Mobile Phone → `device_code` field on Item; SIM Card → `sim_number` field on Item
- add_item.html hides gender/size and shows the correct extra field via JS when a special category is selected
- Validation is in `ItemForm.clean()` (not `Item.clean()`, since `Item.save()` doesn't call `full_clean()`)

**Auto-assignment** (`_try_auto_assign_special(item, by_user=None, note_reason=None)` in views.py):
- Called from `add_item` view after each item is saved
- Also called from `cancel_reservation` (after special item freed) with `note_reason="cancellation"`
- Also called from `reassign_item` (after SR re-queued, if another item available) with `note_reason="item given on walk"`
- Also called from `process_special_lapses` (Pass 2) after lapses free up the queue
- Finds oldest active request for the same category (`order_by("requested_at")`)
- Collection date = next occurrence of the same weekday as `req.requested_at` (`_next_walk_day(req.requested_at.weekday())`) — preserves the walk day
- Creates Reservation via `res.save()` (cascades item→reserved), then `SpecialRequest.objects.filter(pk=...).update(status="fulfilled", ...)`
- Reservation note: `"Re-assigned following {note_reason} (originally requested {date})."` when `note_reason` is set; otherwise `"Special request auto-assigned (originally requested {date})."`

**Lapse management command:** `inventory/management/commands/process_special_lapses.py`
Run daily AFTER `process_lapses` (so freed items get re-queued in the same daily job):
```
... && python manage.py process_special_lapses >> lapses.log 2>&1
```

Pass 1 — lapse stale: `last_confirmed_at < now - 28 days` → `status="lapsed"` via `QuerySet.update()`
Pass 2 — re-assign available special items to next in queue (FIFO by `requested_at`)

**"Still Active" confirmation:** Any volunteer can press it; updates `last_confirmed_at=now()` via `QuerySet.update()`. Queue position (original `requested_at`) is unchanged.

- **Volunteer page:** button renders as solid green "Confirmed" (disabled, `opacity:1`) if confirmed today, otherwise shows "Still Active". Checked with `{% now "Y-m-d" as today_date %}` and `sr.last_confirmed_at|date:"Y-m-d" == today_date`. After confirming, redirects to `/inventory/volunteer/?tab=special`.
- **Admin page:** "Confirmed" badge appears inline in the Status column when confirmed today. Actions column shows an icon-only check-circle button only if not yet confirmed today.

Cancel button on both pages uses a Bootstrap modal for confirmation.

**Volunteer view:** 3rd toggle tab "Requests" alongside Available/Reserved. Shows all active requests with "Still Active" button. Own requests get a "Cancel" button. A "Today's collections" section appears above the requests list showing fulfilled SRs whose `reserved_for_date` is today — with a packed/unpacked visual distinction (blue border + "Packed ✓" badge vs yellow border + "Not packed yet") and a View button to mark collected.

My Reservations (top of volunteer page) excludes items auto-assigned via special request:
```python
my_res = Reservation.objects.filter(reserved_by=request.user, status="reserved"
).exclude(item__fulfilled_special_request__status="fulfilled")
```
`fulfilled_special_request` is the `related_name` on `SpecialRequest.fulfilled_by_item`.

**Admin view:** `/inventory/special-requests/` — paginated (10/page), layout matches missed_collections (same header, logo, Beta badge). Filter pills: Active / Collected / Lapsed (no default highlighted; Clear appears when a filter is active). Default view (no pill active) shows active + assigned (fulfilled with item not yet given). Status column shows: Active (yellow) + optional "Confirmed" badge (green) if confirmed today; Assigned (blue, item reserved/packed); Collected (green, item given); Lapsed (grey) — all derived from `sr.status` + `sr.fulfilled_by_item.status` in the template, no extra model field needed. "Info" column in inventory shows yellow "Special" badge for `category.is_special` items.

**Special filter pill** on inventory table: `?status=special` → `category__is_special=True` + excludes given.

## Test setup scripts

**`seed_categories.py`** — run once (or re-run safely, uses `get_or_create`):
```bash
python manage.py shell < seed_categories.py
```
Creates 16 standard categories + 3 special-request categories (Tent TE, Mobile Phone PH, SIM Card SI) with 2-char codes, UK size options (clothing XS–XXXL, trousers 28–42" waist, shoes UK 3–13), and 7 routes with exact brand colours. Safe to re-run — uses `get_or_create` throughout.

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
- Restart after code changes: `sudo systemctl restart uos-inventory`
