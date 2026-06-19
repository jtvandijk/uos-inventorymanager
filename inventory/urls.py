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
    pack_all_items,
    collect_item,
    view_item,
    get_next_code,
    volunteer_view,
    run_sheet_view,
    missed_collections_view,
    create_special_request,
    view_special_request,
    edit_special_request,
    admin_special_requests_view,
    confirm_special_request,
    cancel_special_request,
    signup_view,
    users_view,
    approve_user,
    reject_user,
    delete_user,
    activity_log_view,
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
    # Special Requests
    # ---------------------------
    path("special-request/new/", create_special_request, name="create_special_request"),
    path("special-request/<int:sr_id>/", view_special_request, name="view_special_request"),
    path("special-request/<int:sr_id>/edit/", edit_special_request, name="edit_special_request"),
    path("special-requests/", admin_special_requests_view, name="admin_special_requests"),
    path("special-request/<int:sr_id>/confirm/", confirm_special_request, name="confirm_special_request"),
    path("special-request/<int:sr_id>/cancel/", cancel_special_request, name="cancel_special_request"),

    # ---------------------------
    # Run Sheet
    # ---------------------------
    path("run-sheet/", run_sheet_view, name="run_sheet"),
    path("pack-all/", pack_all_items, name="pack_all_items"),

    # ---------------------------
    # Sign-up & User Approval
    # ---------------------------
    path("signup/", signup_view, name="signup"),
    path("users/", users_view, name="users"),
    path("users/<int:user_id>/approve/", approve_user, name="approve_user"),
    path("users/<int:user_id>/reject/", reject_user, name="reject_user"),
    path("users/<int:user_id>/delete/", delete_user, name="delete_user"),
    path("activity/", activity_log_view, name="activity_log"),
]