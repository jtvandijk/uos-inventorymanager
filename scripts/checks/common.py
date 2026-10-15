import io
from datetime import date, timedelta

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import Client

from inventory.models import Category, Item, Reservation, Route, SpecialRequest


class Results:
    def __init__(self, section):
        self.section = section
        self.items = []

    def ok(self, name, passed, detail=""):
        self.items.append((name, bool(passed), detail))


def user(username, admin=False):
    u, _ = User.objects.get_or_create(username=username, defaults={"is_active": True})
    if admin:
        u.groups.add(Group.objects.get_or_create(name="Admin")[0])
    return u


def client(u, csrf=False):
    c = Client(enforce_csrf_checks=csrf)
    c.force_login(u)
    return c


def reset_stock():
    SpecialRequest.objects.all().delete()
    Reservation.objects.all().delete()
    Item.objects.all().delete()


def run_daily_jobs():
    out = io.StringIO()
    call_command("process_lapses", stdout=out)
    call_command("process_special_lapses", stdout=out)


def age_reservations(days):
    """Pretend `days` have passed for every open reservation."""
    for r in Reservation.objects.filter(status__in=["reserved", "packed"]):
        Reservation.objects.filter(pk=r.pk).update(reserved_for_date=r.reserved_for_date - timedelta(days=days))


def in_days(n):
    return (date.today() + timedelta(days=n)).isoformat()


def fresh(obj):
    return type(obj).objects.get(pk=obj.pk)


def route():
    return Route.objects.order_by("id").first()


def category(name):
    return Category.objects.get(name=name)
