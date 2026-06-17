# UOS Inventory Manager

A lightweight inventory management system built for [Under One Sky](https://underoneskytogether.com/), a street outreach charity operating in London. The system manages clothing donations distributed across named outreach routes (Waterloo, Kings Cross, etc.).

Built and maintained by a solo volunteer.

## Features

- **Item management** — add items in bulk, auto-generate unique item codes per category (e.g. `UOS-JA00001`), edit and delete items
- **Reservations** — reserve items for specific people with a collection date, route, and notes; volunteers can manage their own reservations
- **Workflow** — items move through Available → Reserved → Packed → Collected
- **Reservation lapse** — automated daily job extends uncollected reservations by 7 days on the first miss; releases back to stock on the second miss and logs to Missed Collections
- **Re-assign** — if a reserved item is given to someone else in the field, volunteers can re-assign the reservation to another matching item in stock (or log it as missed if none available)
- **Special requests** — queue-based system for items not normally in stock (tent, mobile phone, SIM card). Items auto-assign to the first person in queue (FIFO) when added to inventory; volunteers confirm requests are still active (button turns green when confirmed today); lapses after 4 weeks without confirmation
- **Run sheet** — per-date, per-route picking list with AJAX pack toggling and print support
- **Missed Collections** — admin log of reservations that lapsed or could not be re-assigned, for tracking patterns over time
- **Two roles** — Admin (full access) and Volunteer (reserve, cancel/edit own reservations, mark collected, re-assign, file special requests)
- **Search & filter** — volunteer view: search by item code, category, or person name; filter by status (Available / Reserved / Packed / Special); sortable columns; paginated
- **Resource hub** — public `/resources/` page with volunteer guidelines, policies, and reference information (no login required)

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

Creates 16 clothing categories and 3 special-request categories (Tent, Mobile Phone, SIM Card) with 2-character codes, UK size options (clothing XS–XXXL, trousers 28–42" waist, shoes UK 3–13), and the 7 outreach routes with their colours.

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

## Special request lapse (automated)

Special requests that are not confirmed within 4 weeks are automatically lapsed, and any available special-category items are auto-assigned to the next person in queue. This is handled by a second daily management command:

```bash
python manage.py process_special_lapses
```

**Two-pass logic:**
- **Pass 1** — lapses any active special request where `last_confirmed_at` is older than 28 days
- **Pass 2** — for each available special-category item, finds the oldest active request for that category and creates a reservation (collection date = next occurrence of the same weekday the request was originally filed)

### Cron setup (production server)

Add both commands to crontab with `crontab -e`. Run `process_special_lapses` immediately after `process_lapses` so released items are re-queued in the same daily job:

```
0 7 * * * /path/to/venv/bin/python /path/to/manage.py process_lapses >> /path/to/logs/lapses.log 2>&1 && /path/to/venv/bin/python /path/to/manage.py process_special_lapses >> /path/to/logs/lapses.log 2>&1
```

Adjust paths to match your server. Both commands are idempotent — safe to run multiple times on the same day.

## Production

Uses a separate `settings_prod.py`:

```bash
DJANGO_SETTINGS_MODULE=stockmanager.settings_prod gunicorn stockmanager.wsgi
```

Nginx proxies to Gunicorn with `X-Forwarded-Proto` headers for HTTPS.

- Server: Linode VPS at `178.79.153.239`
- Domain: `uos-inventory.duckdns.org` (DuckDNS + Let's Encrypt)
- After template/static changes: `python manage.py collectstatic`
- After code changes: `sudo systemctl restart uos-inventory`

## Roles

| Action | Volunteer | Admin |
|---|---|---|
| View inventory | | ✓ |
| Add / edit / delete items | | ✓ |
| Reserve items | ✓ | ✓ |
| Edit any reservation | ✓ | ✓ |
| Cancel own reservations | ✓ | ✓ |
| Cancel any reservation | | ✓ |
| Re-assign reservation | ✓ | ✓ |
| Mark as packed / unpacked | | ✓ |
| Mark as collected | ✓ | ✓ |
| File / confirm / cancel special requests | ✓ | ✓ |
| Run sheet | | ✓ |
| Missed Collections log | | ✓ |
| Special Requests admin log | | ✓ |
