# Deploying changes to the server

Run these after changes have been pushed to GitHub. Before pushing, run the checks on your laptop: `venv/bin/python scripts/checks/run.py` (see [checks.md](checks.md)).

Server: `justin@178.79.153.239` · app folder: `/home/justin/uos-inventorymanager` · service: `uos-inventory`

## Every update

```bash
ssh justin@178.79.153.239
cd ~/uos-inventorymanager

# 1. Back up the database (this name is git-ignored)
cp db.sqlite3 db-backup-$(date +%F).sqlite3

# 2. Get the new code
git pull

# 3. Use the venv and production settings
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=stockmanager.settings_prod

# 4. Apply database changes (harmless if there are none)
python manage.py migrate

# 5. Copy static files (logo, favicon) to where Nginx serves them
python manage.py collectstatic --noinput

# 6. Restart Gunicorn so it loads the new code and templates
sudo systemctl restart uos-inventory
sudo systemctl status uos-inventory --no-pager    # should say "active (running)"
```

Then open https://uos-inventory.duckdns.org and click through the pages you changed.

## Nginx

Nginx doesn't need restarting for app changes. Only if its own config changed:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## If something goes wrong

**Site shows 502 Bad Gateway** — Gunicorn didn't start. See why:

```bash
sudo journalctl -u uos-inventory -n 50 --no-pager
```

**Roll back to the previous version:**

```bash
cd ~/uos-inventorymanager
git log --oneline -5                 # find the commit before the update
git checkout <commit>
sudo systemctl restart uos-inventory
```

Go back to the latest code later with `git checkout master && git pull`.

**Restore the database** (only if data went wrong, not for code problems):

```bash
sudo systemctl stop uos-inventory
cp db-backup-YYYY-MM-DD.sqlite3 db.sqlite3
sudo systemctl start uos-inventory
```

## Daily jobs (cron)

The reservation and special-request lapse rules run once a day from cron. Check with `crontab -l`; the line should be:

```
0 7 * * * cd /home/justin/uos-inventorymanager && DJANGO_SETTINGS_MODULE=stockmanager.settings_prod venv/bin/python manage.py process_lapses >> lapses.log 2>&1 && DJANGO_SETTINGS_MODULE=stockmanager.settings_prod venv/bin/python manage.py process_special_lapses >> lapses.log 2>&1
```

Edit with `crontab -e`. To check it ran: `tail -20 ~/uos-inventorymanager/lapses.log` should show a "Done: ..." line from this morning.

Run them by hand (e.g. to test):

```bash
cd ~/uos-inventorymanager && source venv/bin/activate
export DJANGO_SETTINGS_MODULE=stockmanager.settings_prod
python manage.py process_lapses
python manage.py process_special_lapses
```

## Occasionally

- **Old backups:** `ls db-backup-*` and delete ones you no longer need.
- **SSL certificate:** renews automatically (certbot cron at 12:00). Check with `sudo certbot certificates`.
- **Server updates:** `sudo apt update && sudo apt upgrade`, then `sudo systemctl restart uos-inventory`.
