"""Item page actions submitted like a browser would (CSRF on, form actions read from the HTML)."""
import html
import re
from datetime import date, timedelta
from urllib.parse import quote, unquote

from inventory.models import Item, Reservation

from common import Results, category, client, in_days, reset_stock, route, user

# Contains & and a space on purpose: that's what broke the nested ?next= before
NEXT = "/inventory/volunteer/?status=reserved&search=coat L"
BACK = re.compile(r'<a href="([^"]+)" class="btn btn-outline-secondary">\s*Back')


def run():
    R = Results("Redirects & forms")
    c = client(user("chk_redirect_admin", admin=True), csrf=True)
    coat = category("Coat")
    reset_stock()
    sizes = iter(range(1000))

    def reserved_item(size=None):
        it = Item(category=coat, gender="male", size=size or f"T{next(sizes)}")
        it.save()
        Reservation(item=it, person="Ann", route=route(), reserved_for_date=date.today() + timedelta(days=3)).save()
        return it

    def item_page(it):
        h = c.get(f"/inventory/item/{it.id}/?next={quote(NEXT, safe='')}").content.decode()
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', h).group(1)
        forms = re.findall(r'<form method="post" action="([^"]+)"[^>]*>.*?<button type="submit"[^>]*>([^<]+)</button>', h, re.S)
        return token, [(html.unescape(a), label.strip()) for a, label in forms], html.unescape(BACK.search(h).group(1))

    def press(it, label):
        token, forms, _ = item_page(it)
        action = next(a for a, l in forms if l == label)
        return c.post(action, {"csrfmiddlewaretoken": token})

    def back_after(resp):
        return html.unescape(BACK.search(c.get(resp["Location"]).content.decode()).group(1))

    it = reserved_item()
    R.ok("item page: Back goes to where you came from", item_page(it)[2] == NEXT)

    r = press(it, "Mark as Packed")
    R.ok("pack: returns to item page", r["Location"].startswith(f"/inventory/item/{it.id}/"), r.get("Location"))
    R.ok("pack: Back still goes to where you came from", back_after(r) == NEXT, back_after(r))
    r = press(it, "Mark as Unpacked")
    R.ok("unpack: applied", Item.objects.get(pk=it.pk).status == "reserved")

    r = press(it, "Yes, Cancel It")
    R.ok("cancel: returns to item page, Back intact", back_after(r) == NEXT, back_after(r))
    R.ok("cancel: applied", Item.objects.get(pk=it.pk).status == "available")

    it = reserved_item()
    r = press(it, "Item Collected")
    R.ok("collect: goes to where you came from", unquote(r["Location"]) == NEXT, r.get("Location"))

    it = reserved_item()
    r = press(it, "Confirm")
    R.ok("reassign, no spare: goes to where you came from", unquote(r["Location"]) == NEXT, r.get("Location"))

    it = reserved_item("TSPARE")
    spare = Item(category=coat, gender="male", size="TSPARE")
    spare.save()
    r = press(it, "Re-assign")
    R.ok("reassign to spare: opens the spare, Back intact",
         r["Location"].startswith(f"/inventory/item/{spare.id}/") and back_after(r) == NEXT, r.get("Location"))

    it = reserved_item()
    r = press(it, "Delete")
    R.ok("delete: goes to where you came from", unquote(r["Location"]) == NEXT and not Item.objects.filter(pk=it.pk).exists())

    it = Item(category=coat, gender="male", size="TRES")
    it.save()
    h = c.get(f"/inventory/item/{it.id}/?next={quote(NEXT, safe='')}").content.decode()
    reserve_url = html.unescape(re.search(r'<a href="([^"]+)"\s+class="btn btn-success">', h).group(1))
    h = c.get(reserve_url).content.decode()
    r = c.post(reserve_url, {
        "csrfmiddlewaretoken": re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', h).group(1),
        "next": html.unescape(re.search(r'name="next" value="([^"]*)"', h).group(1)),
        "person": "Res", "route": route().id, "reserved_for_date": in_days(7), "notes": ""})
    R.ok("reserve: returns to item page, Back intact", back_after(r) == NEXT, r.get("Location"))

    it = reserved_item()
    urls = [f"/inventory/pack/{it.id}/", f"/inventory/cancel/{it.id}/", f"/inventory/collect/{it.id}/",
            f"/inventory/item/{it.id}/reassign/", f"/inventory/delete/{it.id}/"]
    R.ok("actions refuse plain visits (GET)", all(c.get(u).status_code == 405 for u in urls))
    R.ok("plain visits changed nothing", Item.objects.get(pk=it.pk).status == "reserved")
    r = c.post(f"/inventory/delete/{it.id}/")
    R.ok("POST without CSRF token refused", r.status_code == 403 and Item.objects.filter(pk=it.pk).exists())

    return R
