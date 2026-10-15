# CLAUDE.md — Under One Sky Inventory Manager

## Project
Django inventory management app for Under One Sky, a London street outreach charity.
Manages clothing donations distributed across named outreach routes (Waterloo, Kings Cross, etc.).
Built and maintained by a solo volunteer. Keep solutions simple — no over-engineering.

## Stack
- Django 5.2 LTS (pinned in `requirements.txt`, security fixes until April 2028; next step is 6.2 LTS, together with a server OS upgrade — the server runs Ubuntu 22.04 / Python 3.10, which Django 6 doesn't support), SQLite
- Never run `makemigrations` on the server; migrations are made on the laptop and pulled via git
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
- `add_role_context` also injects `pending_count` (inactive user count) for admins — powers the red badge on the Users nav item across all admin pages
- Volunteers: reserve items, edit any reservation, cancel their own reservations, mark items collected, re-assign, file/confirm/cancel special requests
- Admins: everything, including pack/unpack, add/edit/delete items, run sheet, missed collections, special requests admin log, user management, activity log

## Item workflow
`available` → `reserved` → `packed` → `given` (displayed as "Collected")

Status lives on both `Item.status` and `Reservation.status` — `Reservation.save()` cascades to `Item`.

## Item codes
Format: `UOS-{CATEGORY_CODE}{00001}` — auto-generated on `Item.save()` when code is blank.
Category codes are 2-character uppercase strings. Never let users edit item codes.

## Key patterns

**`next` parameter:** All action views accept a `?next=` param for redirect-after-action.
On `view_item`, actions that should come back to the item page use `return_here` (built in the view: the item URL with the original `next`, URL-encoded as a whole so `&`s in `next` survive):
```
action="{% url 'pack_item' item.id %}?next={{ return_here }}"
```
Never build the nested `?next=...?next=...` in the template — it only encodes once and drops everything after the first `&`.

**State-changing actions are POST-only** (`@require_POST`): cancel_reservation, pack_item, collect_item, reassign_item, delete_item, confirm/cancel_special_request. In templates they are `<form method="post" action="...?next=...">` + `{% csrf_token %}` — keep `next` in the action's query string, since the views read `request.GET["next"]`. The run sheet pack toggle POSTs via `fetch` with the `X-CSRFToken` header.

**AJAX detection:** Used in two places — run sheet (pack toggle) and volunteer view (item list + SR list).
Check with `request.headers.get("x-requested-with") == "XMLHttpRequest"`.
In `volunteer_view`, distinguish which partial to return via `request.GET.get("type")`: `"sr"` returns `_sr_list.html`, anything else returns `_item_list.html`.
Do NOT add Django messages inside AJAX-handled branches — they accumulate silently.

**Size options:** Populated via AJAX (`/inventory/get-sizes/?category_id=X`) on category change.
On edit forms, pre-populate sizes on page load and pre-select the current value.

**Flash messages:** `view_item.html` displays Django messages at the top of the card with 5s auto-dismiss.
Inventory list also shows messages. Other pages do not — don't assume messages show everywhere.

## Templates
- All pages extend `inventory/templates/base.html` (blocks: `title`, `extra_head`, `content`); partials (`_item_list.html`, `_sr_list.html`) don't
- `base.html` loads Bootstrap CSS + JS bundle and Bootstrap Icons from CDN (not collected static); the JS bundle is in `<head>` so inline page scripts can use `bootstrap`
- Each page still has its own header markup (logo, title, Beta badge) inside `content`
- Admin nav is one include: `{% include "inventory/_admin_nav.html" with active="missed" %}` (keys: overview, inventory, special, missed, run_sheet, users, activity)
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
- Pushes `reserved_for_date` forward 7 days (repeating +7 until it is today or later, so after downtime the grace week still lands on a future same-weekday walk), sets `auto_extended=True`, appends note
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
- If the item fulfilled a SpecialRequest, re-point `fulfilled_by_item` to the replacement (otherwise the SR would show as Collected)
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

## Delete item

`delete_item` (admin): if the item fulfilled a SpecialRequest, that SR goes back to `active` (original queue position) before the item is deleted, then another available item of the category is auto-assigned with `note_reason="item deleted"`. Regular reservations are cascade-deleted with the item.

## Cancel reservation

`cancel_reservation` calls `reservation.delete()` which sets `item.status = "available"` via the model override.

**For special items:** before deleting the reservation, the linked `SpecialRequest` (`fulfilled_by_item=item, status="fulfilled"`) is lapsed (`status="lapsed"`). After delete, `_try_auto_assign_special` fires immediately to give the item to the next person in queue. Cancelling is a deliberate volunteer action meaning the person no longer needs the item — the SR is done.

**For regular items:** just `reservation.delete()`. Item returns to available. No queue to re-assign to.

## Special request system

Handles items not normally in stock (Backpack, Sleeping Bag, Tent, Mobile Phone, SIM Card). Categories are flagged with `Category.is_special=True`.

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
- `Category.extra_field` choices: `none` / `device_code` / `sim_number`
- Mobile Phone → `device_code` field on Item; SIM Card → `sim_number` field on Item
- add_item.html and edit_item.html both hide gender/size and show the correct extra field via JS when a special category is selected; both use `categories_data_json` (server-injected) to drive show/hide on category change
- `view_item.html` shows a Device Code or SIM Number row when `item.category.extra_field != "none"`
- `ItemEditForm` includes `device_code` and `sim_number` fields (in addition to category/gender/size)
- Validation is in `ItemForm.clean()` (not `Item.clean()`, since `Item.save()` doesn't call `full_clean()`)

**Auto-assignment** (`_try_auto_assign_special(item, by_user=None, note_reason=None)` in views.py):
- Called from `add_item` view after each item is saved
- Also called from `cancel_reservation` (after special item freed) with `note_reason="cancellation"`
- Also called from `reassign_item` (after SR re-queued, if another item available) with `note_reason="item given on walk"`
- Also called from `process_special_lapses` (Pass 2) after lapses free up the queue
- Finds oldest active request for the same category (`order_by("requested_at")`)
- Collection date = next occurrence of the same weekday as `req.requested_at` (`_next_walk_day(req.requested_at.weekday())`) — preserves the walk day
- Reservation `reserved_by` = the SR's `requested_by` (falls back to `by_user`), so the volunteer who filed it can cancel it
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

- **Volunteer page:** Still Active and Cancel Request live on `view_special_request` (detail page), not on the SR list card. The card has a single View button (same style as item cards). Checked with `{% now "Y-m-d" as today_date %}` and `sr.last_confirmed_at|date:"Y-m-d" == today_date` — confirmed today renders as disabled green button.
- **Admin page:** "Confirmed" badge appears inline in the Status column when confirmed today. Actions column shows an icon-only check-circle button only if not yet confirmed today.

**`view_special_request`** (`/inventory/special-request/<id>/`) — detail page for any SR, accessible to all logged-in users. Shows person, category, route, status, dates, notes, assigned item link. For active SRs: Still Active button (any volunteer) and Cancel Request button (requester or admin, modal-confirmed) right-aligned above a Back button on the left — same layout as `view_item`. Cancel redirects to `?next` param.

**Volunteer view tabs:** Four tabs — **Inventory** (available stock), **Reserved** (reserved + packed items), **Today** (everything due for collection today's walk), **Requests** (SR queue). The Requests tab button is yellow (`btn-warning`); the others use blue (`btn-primary`). Tab switching is JS-driven (`showTab()`); Inventory/Reserved use AJAX for the item list; Today and Requests are server-rendered.

**Today tab:** Shows regular reservations and SR assignments due today, split into two sections (Reservations / Special requests), each sorted by route then person. SR-assigned items are excluded from the Reservations section (appear only in Special requests). Empty state: "No collections scheduled for today." Back-navigation from `view_item` returns to `?tab=today`.

```python
today_reservations = Reservation.objects.filter(
    reserved_for_date=today, status__in=["reserved","packed"]
).exclude(item__fulfilled_special_request__status="fulfilled")

today_srs = SpecialRequest.objects.filter(
    status="fulfilled",
    fulfilled_by_item__status__in=["reserved","packed"],
    fulfilled_by_item__reservation__reserved_for_date=today,
)
```

**SR list (Requests tab, 5/page):** Shows active + assigned SRs (fulfilled with item not yet given) — not just active. Cards show Active (yellow) or Assigned (blue) badge. Last-confirmed date only shown for active SRs. AJAX-paginated via `_sr_list.html` partial. Pagination uses `<button onclick="updateSRList(N)">` — not `<a href>` links. Do NOT add per-SR cancel modals to the partial — they get wiped on every AJAX refresh. Cancel lives on `view_special_request` instead.

```python
sr_qs = SpecialRequest.objects.filter(
    Q(status="active") |
    Q(status="fulfilled", fulfilled_by_item__status__in=["reserved","packed"])
)
```

**My Reservations** (top of the Reserved tab, above the search, hidden on other tabs and when empty; 3/page, pager only when >1 page; followed by an "All reservations" heading): includes reserved + packed items, shows route badge and Packed ✓ badge. Excludes SR auto-assigns. Pagination links include `?status=reserved` so page reloads restore the correct tab.

```python
my_res = Reservation.objects.filter(
    reserved_by=request.user, status__in=["reserved","packed"]
).exclude(item__fulfilled_special_request__status="fulfilled")
```
`fulfilled_special_request` is the `related_name` on `SpecialRequest.fulfilled_by_item`.

**My Requests** (top of the Requests tab, under New Special Request, hidden when empty; server-rendered, 3/page, pager only when >1 page; followed by an "All requests" heading, then the SR search + list): shows the logged-in user's own active + assigned SRs. Active shows yellow badge; Assigned shows blue badge. Pagination links include `?tab=special` so reloads restore the Requests tab.

**Admin view:** `/inventory/special-requests/` — paginated (10/page), layout matches missed_collections (same header, logo, Beta badge). Filter pills: Active / Collected / Lapsed (no default highlighted; Clear appears when a filter is active). Default view (no pill active) shows active + assigned (fulfilled with item not yet given). Status column shows: Active (yellow) + optional "Confirmed" badge (green) if confirmed today; Assigned (blue, item reserved/packed); Collected (green, item given); Lapsed (grey) — all derived from `sr.status` + `sr.fulfilled_by_item.status` in the template, no extra model field needed. "Info" column in inventory shows yellow "Special" badge for `category.is_special` items.

**Special filter pill** on inventory table: `?status=special` → `category__is_special=True` + excludes given.

## User accounts

Volunteers self-register at `/inventory/signup/` (no login required). Accounts are created with `is_active=False` and cannot log in until an admin approves them.

**Sign-up form fields:** username (lowercase letters/numbers only, validated by `SignUpForm.clean_username()`), first name, last name, email, phone — all required. Password + confirm password via `UserCreationForm`.

**`UserProfile` model** — OneToOne to `User`, stores `phone`:
```python
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=20, blank=True, default="")
```
Created immediately after user in `signup_view`. Existing users without a profile get an empty phone — access via `profile_phones = {p.user_id: p.phone for p in UserProfile.objects.filter(user__in=page_obj.object_list)}` in the view (avoids `RelatedObjectDoesNotExist`).

**User management** (`/inventory/users/`) — admin-only. Lists all users paginated (15/page, numbered elided range). Columns: username, first/last name, email, phone, role badge (Admin/Volunteer/Pending). Actions: Approve + Reject for pending accounts; Delete (with modal) for any non-superuser except yourself.

Admin accounts are created manually via Django admin (`/admin/`) and assigned to the `"Admin"` group. Sessions last 2 weeks by default (`SESSION_COOKIE_AGE`); no auto-logout configuration needed.

## Activity log

**`ActivityLog` model:**
```python
user = ForeignKey(User, on_delete=SET_NULL, null=True)
action = CharField(max_length=20, choices=[...])  # see below
item_code = CharField(max_length=20, blank=True)  # stored as string — survives item deletion
person = CharField(max_length=100, blank=True)
route_name = CharField(max_length=100, blank=True)  # stored as string — survives route deletion
detail = CharField(max_length=200, blank=True)
timestamp = DateTimeField(auto_now_add=True)
```

**Action choices:** `reserve`, `edit_reservation`, `cancel_reservation`, `collect`, `reassign`, `new_sr`, `confirm_sr`, `cancel_sr`.

**Helper:** `_log(user, action, item=None, item_code="", person="", route=None, detail="")` in `views.py`. Pass `item` (FK object) or `item_code` (string); route as FK object (name extracted). Called directly in each relevant view after the action succeeds.

**Not logged:** add item, auto-assign (system action), pack/unpack (admin prep action).

**Admin view** (`/inventory/activity/`) — paginated (25/page, numbered elided range). Ordered by `-timestamp`. No filters — keep it simple.

## Admin overview

`/inventory/overview/` — admin-only, read-only, no pagination. Three sections:
- **Stock available:** one table per size type (non-special categories × sizes, available items only). Size columns with no stock in that table are dropped. Amber = 1–2, red total = 0.
- **Special requests demand vs stock:** per special category: waiting (active), assigned (fulfilled, item reserved/packed), in stock, shortfall = max(waiting − in stock, 0).
- **Impact:** this month / last month / last 12 months — items given (`Item.given_at`), distinct person names on given reservations, SRs fulfilled, missed collections (`missed_at`), missed rate.

## Volunteer filter chips

Inventory tab only (`status=available`). `_apply_chips()` in views.py reads `cat`, `gender`, `size` GET params. Chips render at the top of `_item_list.html` and are recomputed on every AJAX refresh. Only in-stock options are listed. Picking a gender keeps unisex items. Changing category clears gender/size; switching tabs clears all chips (`clearChips()`).

Reserved tab has **route chips** instead (`_apply_route_chips()`, GET param `route`): one per route with open reservations, active chip filled in the route's colour; filters the "All reservations" list.

## Run sheet

`/inventory/run-sheet/` — admin-only. Filter by date + route (optional). Shows all reserved + packed items for that date as a table with individual Pack/Packed ✓ toggle buttons (AJAX via `pack_item`).

**Pack all / Unpack all button:** Appears whenever the run sheet has results. Shows "Pack N item(s)" when any items are unpacked; switches to "Unpack N item(s)" when all are packed. POSTs to `pack_all_items` view with `action=pack` or `action=unpack`. Uses `QuerySet.update()` on both Reservation and Item directly (same bypass-cascade pattern as lapse system) — does not call `Reservation.save()`.

```python
# pack_all_items view — POST only, admin only
qs = Reservation.objects.filter(reserved_for_date=target_date, status=source_status)
if route_id:
    qs = qs.filter(route_id=route_id)
item_ids = list(qs.values_list("item_id", flat=True))
qs.update(status=target_status)
Item.objects.filter(id__in=item_ids).update(status=target_status)
```

## Size options

The size list is fixed in migration `0014_canonical_sizes.py` (`SIZES`): clothing XS–XXXL, trousers W28–W42 (every inch), shoes UK 3–UK 13. `Item.size` stores the value (`"L"`, `"32"`, `"7"`); templates show `item.get_size_label` (`"W32"`, `"UK 7"`) — never `item.size` directly. Size options are view-only in Django admin; to change the list, add a new data migration. Overview and filter chips order sizes by `SizeOption.id`, so recreate options in display order.

## Checks

`venv/bin/python scripts/checks/run.py` (or `--quick`) — run before pushing. Builds a throwaway DB (migrate + `seed_categories.py`), then runs `check_rules.py` (one check per rule), `check_redirects.py` (item page forms + Back), `check_stress.py` (random actions + consistency rules). When fixing a bug, add a check for it. See `docs/checks.md`.

## Test setup scripts

**`seed_categories.py`** — run once (or re-run safely, uses `get_or_create`):
```bash
python manage.py shell < seed_categories.py
```
Creates 12 standard categories + 5 special-request categories (Backpack BP, Sleeping Bag SL, Tent TE, Mobile Phone PH, SIM Card SI) with 2-char codes, and 7 routes with exact brand colours. Size options come from migration 0014, not this script. Safe to re-run — uses `get_or_create` throughout.

**`seed_data.py`** — wipes items and reservations only (preserves users, categories, routes, sizes):
```bash
python manage.py shell < seed_data.py
```
Creates 50 items: ~88% available, ~8% reserved, ~2% packed, ~2% collected.

**`seed_demo.py`** — run after `seed_data.py` + `seed_categories.py` to set up demo scenarios: phone queue (waiting 9 weeks / 3 weeks / 2 days, none in stock — add a phone live and it goes to the longest-waiting person), sleeping bag + backpack queues, today's Waterloo walk (3 collections, 1 packed), one grace-week reservation, and 3 months of handed-out/missed history for the impact numbers.

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
