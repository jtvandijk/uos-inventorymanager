# Live demo

A 10-minute walk through the app for a meeting. Set it up on the day of the demo, because "today's walk" means the day you run the setup.

## 1. Set up (on the server, same day)

```bash
ssh justin@178.79.153.239
cd ~/uos-inventorymanager
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=stockmanager.settings_prod

git pull                                     # make sure seed_demo.py is there
sudo systemctl restart uos-inventory

python manage.py shell < seed_data.py        # wipes items, reservations, requests; fresh fake stock
python manage.py shell < seed_categories.py  # adds back a tent, phone and SIM
python manage.py shell < seed_demo.py        # demo scenarios on top
```

The last command should end with:

```
Phone queue: 3 waiting, 0 in stock
Today's walk (Waterloo): 3 collections
Handed out in the last 90 days: ...
```

Users, categories and routes are never touched.

## 2. What the setup creates

| Scenario | Details | Where you see it |
| --- | --- | --- |
| Phone queue, none in stock | Marek D (waiting 9 weeks), Grace O (3 weeks), Tom W (1 week) | Overview, Requests tab |
| Other queues | Sleeping bag: Ahmed K, Lisa C. Backpack: Sophie W | Overview shortfall |
| Today's Waterloo walk | James S (already packed), Maria T, Ryan H | Today tab, Run Sheet |
| Next week's Waterloo walk | Nina J, Carlos G | Reserved tab |
| A grace-week reservation | Patrick F, missed once, moved to next week | Orange clock icon on the item page |
| Three months of history | About 25 items handed out, 3 missed collections | Overview impact numbers |

## 3. The demo, step by step

Log in as admin. Show steps 2–5 on a phone if you can.

| # | Do this | Point out |
| --- | --- | --- |
| 1 | Log in. You land on the **Overview**. | Stock by category and size at a glance. **Phones: 3 waiting, 0 in stock**: a ready-made donor ask. Items handed out this month / last month / this year, with nobody counting. |
| 2 | Tap **Volunteer View**. It opens on **Today**. | Today's Waterloo collections in one list, one already packed. This is what a walker looks at on the street. |
| 3 | **Inventory** tab: tap **Coat**, **Male**, **L**. Open one, tap **Reserve**. Enter a name, pick **Waterloo**, save. | Three taps to find the right coat. The collection date is already set to next week; the route is remembered for next time. |
| 4 | **Reserved** tab: tap the **Waterloo** chip. Search **Patrick**, open it. | Filter by route. Patrick missed his collection, so it moved to next week automatically (clock icon). Miss again and the coat goes back to stock. Nothing is held forever. |
| 5 | **Requests** tab. Open **Tom W**. | The phone queue in order of who asked first. **Still Active**: volunteers confirm every 4 weeks, otherwise the request lapses, so the queue stays real. |
| 6 | Back to admin: **Inventory → + Add Item**, category **Mobile Phone**, any device code, save, then **Back to Inventory**. | The message says the phone went to **Marek D**, who has waited 9 weeks, not Tom, who asked a week ago. Nobody had to remember. **This is the moment for the phone story.** |
| 7 | **Run Sheet**: today's date, route **Waterloo**, then **Pack … items** (usually 2). | The packing list for a walk, by route. One tap packs the lot. |
| 8 | Volunteer view → **Today** → open **Maria T** → **Item Collected**. | Done on the street in one tap. It's in the impact numbers straight away. |

Optional if there's time: on any reserved item, show **Re-assign** (the item goes to someone else on the walk; the app finds an identical spare or records the miss).

## 4. Reset

To rehearse and then run it again (for example after step 6 used up Marek's place), run the same three commands:

```bash
python manage.py shell < seed_data.py
python manage.py shell < seed_categories.py
python manage.py shell < seed_demo.py
```

Running `seed_demo.py` on its own adds a second set on top rather than resetting, so always run all three. Rehearsal clicks stay in the Activity log; that page isn't part of the demo.

## 5. If something looks off

- **Today tab is empty:** the setup ran on a different day. Re-run the three commands.
- **The phone went to someone other than Marek:** a phone was added during rehearsal. Reset.
- **Add Item won't save a phone:** Mobile Phone needs a device code; type anything.
- **No route pre-filled when reserving:** it remembers your last route, so the first reservation needs one pick.
- **Site shows 502:** `sudo systemctl restart uos-inventory`, then `sudo journalctl -u uos-inventory -n 50 --no-pager` if it persists.

## 6. For the conversation

The shared proposal doc (see `proposal.md` for a snapshot) has the selling points, the needs table with a Zoho column to fill in together, and how the app fits the Zoho warehouse plan. The question to leave with: **who will build and maintain the walk rules, whichever system they live in?**
