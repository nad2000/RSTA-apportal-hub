from django.contrib import admin

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["email", "name"]
    list_filter = ("created_at", "updated_at")
    search_fields = ("name",)
    date_hierarchy = "created_at"
