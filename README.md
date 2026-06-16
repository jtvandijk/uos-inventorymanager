# UOS Inventory Manager

A lightweight inventory management system built for [Under One Sky](https://underoneskytogether.com/), a street outreach charity operating in London. The system manages clothing donations distributed across named outreach routes (Waterloo, Kings Cross, etc.).

Built and maintained by a solo volunteer.

## Features

- **Item management** — add items in bulk, auto-generate unique item codes per category (e.g. `UOS-JA00001`), edit and delete items
- **Reservations** — reserve items for specific people with a collection date, route, and notes; volunteers can manage their own reservations
- **Workflow** — items move through Available → Reserved → Packed → Collected
- **Reservation lapse** — automated daily job extends uncollected reservations by 7 days on the first miss; releases back to stock on the second miss and logs to Missed Collections
- **Re-assign** — if a reserved item is given to someone else in the field, volunteers can re-assign the reservation to another matching item in stock (or log it as missed if none available)
- **Run sheet** — per-date, per-route picking list with AJAX pack toggling and print support
- **Missed Collections** — admin log of reservations that lapsed or could not be re-assigned, for tracking patterns over time
- **Two roles** — Admin (full access) and Volunteer (reserve, cancel/edit own reservations, mark collected, re-assign)
- **Search & filter** — search by item code, category, or person; filter by status (including combined Pending = reserved + packed); sortable columns; paginated

## Tech stack

- **Backend:** Django 6, SQLite
- **Frontend:** Bootstrap 5.3.3, Bootstrap Icons 1.11.3, vanilla JS
- **Production:** Nginx + Gunicorn, Let's Encrypt SSL via DuckDNS

## Setup (local)

```bash
python -m venv venv
source venv/bin/activate
pip install django pillow

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Create an `Admin` group in Django admin and assign it to admin users. Non-admin authenticated users get the volunteer view.

## Initial data setup

Two seed scripts are provided to bootstrap categories, sizes, routes, and test data.

**Step 1 — categories, sizes and routes** (run once, safe to re-run):

```bash
python manage.py shell < seed_categories.py
```

Creates 16 clothing categories with 2-character codes, UK size options (clothing XS–XXXL, trousers 28–42" waist, shoes UK 3–13), and the 7 outreach routes with their colours.

**Step 2 — test data** (wipes items and reservations, keeps everything else):

```bash
python manage.py shell < seed_data.py
```

Creates 50 items with auto-generated codes and a realistic distribution (~88% available, ~8% reserved, ~2% packed, ~2% collected). User accounts are never touched.

## Reservation lapse (automated)

Reservations that are not collected are handled automatically by a daily management command:

- **First miss** — collection date passes with no collection: date is pushed forward 7 days, a note is appended to the reservation, and a clock icon appears in the inventory.
- **Second miss** — pushed date passes again: item is released back to available stock and the reservation is logged in Missed Collections with reason "Lapsed".
- **Re-assign** — if a reserved item is given to someone else in the field: if a matching item exists in stock, the reservation is moved to it (same date, cron pushes it the next morning); if not, the reservation is logged as "No replacement".

Run manually to test:

```bash
python manage.py process_lapses
```

### Cron setup (production server)

Add to crontab with `crontab -e`:

```
0 7 * * * /path/to/venv/bin/python /path/to/manage.py process_lapses >> /path/to/logs/lapses.log 2>&1
```

Adjust paths to match your server. The command is idempotent — safe to run multiple times on the same day.

## Production

Uses a separate `settings_prod.py`:

```bash
DJANGO_SETTINGS_MODULE=stockmanager.settings_prod gunicorn stockmanager.wsgi
```

Nginx proxies to Gunicorn with `X-Forwarded-Proto` headers for HTTPS.

- Server: Linode VPS at `178.79.153.239`
- Domain: `uos-inventory.duckdns.org` (DuckDNS + Let's Encrypt)
- After template/static changes: `python manage.py collectstatic`
- After code changes: `sudo systemctl restart gunicorn`

## Roles

| Action | Volunteer | Admin |
|---|---|---|
| View inventory | | ✓ |
| Add / edit / delete items | | ✓ |
| Reserve items | ✓ | ✓ |
| Edit / cancel own reservations | ✓ | ✓ |
| Edit / cancel any reservation | | ✓ |
| Re-assign reservation | ✓ | ✓ |
| Mark as packed / unpacked | | ✓ |
| Mark as collected | ✓ | ✓ |
| Run sheet | | ✓ |
| Missed Collections log | | ✓ |
