from django.urls import path
from django.contrib.auth import views as auth_views

from .views import (
    inventory_view,
    get_sizes,
    reserve_item,
    delete_item,
    add_item,
    release_item,
    view_item,
    mark_given,
    get_next_code,
    volunteer_view,
)


urlpatterns = [
    # ---------------------------
    # Inventory (Admin)
    # ---------------------------
    path("", inventory_view, name="inventory"),
    path("add/", add_item, name="add_item"),
    path("delete/<int:item_id>/", delete_item, name="delete_item"),
    path("get-next-code/", get_next_code, name="get_next_code"),

    # ---------------------------
    # Item Actions
    # ---------------------------
    path("item/<int:item_id>/", view_item, name="view_item"),
    path("reserve/<int:item_id>/", reserve_item, name="reserve_item"),
    path("release/<int:item_id>/", release_item, name="release_item"),
    path("given/<int:item_id>/", mark_given, name="mark_given"),

    # ---------------------------
    # AJAX / Helpers
    # ---------------------------
    path("get-sizes/", get_sizes, name="get_sizes"),

    # ---------------------------
    # Volunteer Interface
    # ---------------------------
    path("volunteer/", volunteer_view, name="volunteer"),
]