from django.contrib import admin
from .models import Transaction, Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "t_type", "is_active", "parent", "sort_order")
    list_filter = ("t_type", "is_active")
    search_fields = ("name",)
    ordering = ("sort_order",)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("company", "project", "category", "txn_date", "amount", "currency")
    list_filter = ("currency", "company", "project", "txn_date")
    search_fields = ("description",)
    date_hierarchy = "txn_date"
    ordering = ("-txn_date",)
