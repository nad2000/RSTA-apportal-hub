from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(SimpleHistoryAdmin):
    list_display = ["email", "name"]
    list_filter = ["created_at", "updated_at"]
    search_fields = [
        "email",
    ]
    date_hierarchy = "created_at"
