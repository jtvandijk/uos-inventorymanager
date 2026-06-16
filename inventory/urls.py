from django.urls import path
from django.contrib.auth import views as auth_views

from .views import (
    inventory_view,
    get_sizes,
    reserve_item,
    edit_item,
    edit_reservation,
    reassign_item,
    delete_item,
    add_item,
    add_item_confirm,
    cancel_reservation,
    pack_item,
    collect_item,
    view_item,
    get_next_code,
    volunteer_view,
    run_sheet_view,
    missed_collections_view,
)


urlpatterns = [
    # ---------------------------
    # Inventory (Admin)
    # ---------------------------
    path("", inventory_view, name="inventory"),
    path("add/", add_item, name="add_item"),
    path("add/confirm/", add_item_confirm, name="add_item_confirm"),
    path("delete/<int:item_id>/", delete_item, name="delete_item"),
    path("get-next-code/", get_next_code, name="get_next_code"),

    # ---------------------------
    # Item Actions
    # ---------------------------
    path("item/<int:item_id>/", view_item, name="view_item"),
    path("item/<int:item_id>/edit/", edit_item, name="edit_item"),
    path("reserve/<int:item_id>/", reserve_item, name="reserve_item"),
    path("reservation/<int:reservation_id>/edit/", edit_reservation, name="edit_reservation"),
    path("item/<int:item_id>/reassign/", reassign_item, name="reassign_item"),
    path("missed/", missed_collections_view, name="missed_collections"),
    path("cancel/<int:item_id>/", cancel_reservation, name="cancel_reservation"),
    path("pack/<int:item_id>/", pack_item, name="pack_item"),
    path("collect/<int:item_id>/", collect_item, name="collect_item"),

    # ---------------------------
    # AJAX / Helpers
    # ---------------------------
    path("get-sizes/", get_sizes, name="get_sizes"),

    # ---------------------------
    # Volunteer Interface
    # ---------------------------
    path("volunteer/", volunteer_view, name="volunteer"),

    # ---------------------------
    # Run Sheet
    # ---------------------------
    path("run-sheet/", run_sheet_view, name="run_sheet"),
]