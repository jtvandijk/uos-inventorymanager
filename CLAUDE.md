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
- Volunteers: reserve items, cancel/edit their own reservations, mark items collected
- Admins: everything, including pack/unpack, add/edit/delete items, run sheet

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
