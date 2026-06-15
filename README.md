# UOS Inventory Manager

A lightweight inventory management system built for [Under One Sky](https://underoneskytogether.com/), a street outreach charity operating in London. The system manages clothing donations distributed across named outreach routes (Waterloo, Kings Cross, etc.).

Built and maintained by a solo volunteer.

## Features

- **Item management** — add items in bulk, auto-generate unique item codes per category (e.g. `UOS-JA00001`), edit and delete items
- **Reservations** — reserve items for specific people with a collection date, route, and notes; volunteers can manage their own reservations
- **Workflow** — items move through Available → Reserved → Packed → Collected
- **Run sheet** — per-date, per-route picking list with AJAX pack toggling and print support
- **Two roles** — Admin (full access) and Volunteer (reserve, cancel own reservations, mark collected)
- **Search & filter** — search by item code, category, or person; filter by status; sortable columns; paginated

## Tech stack

- **Backend:** Django 6, SQLite
- **Frontend:** Bootstrap 5.3, vanilla JS
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

## Production

Uses a separate `settings_prod.py`:

```bash
DJANGO_SETTINGS_MODULE=stockmanager.settings_prod gunicorn stockmanager.wsgi
```

Nginx proxies to Gunicorn with `X-Forwarded-Proto` headers for HTTPS.

## Roles

| Action | Volunteer | Admin |
|---|---|---|
| View inventory | | ✓ |
| Add / edit / delete items | | ✓ |
| Reserve items | ✓ | ✓ |
| Edit / cancel own reservations | ✓ | ✓ |
| Edit / cancel any reservation | | ✓ |
| Mark as packed / unpacked | | ✓ |
| Mark as collected | ✓ | ✓ |
| Run sheet | | ✓ |
