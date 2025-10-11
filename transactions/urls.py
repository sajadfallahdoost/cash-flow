from django.urls import path
from .views import (
    transactions_list_create, transactions_rud, transactions_summary,
    categories_list_create, categories_rud,
)

urlpatterns = [
    # Transactions
    path("transactions/", transactions_list_create, name="transactions-list-create"),
    path("transactions/<int:pk>/", transactions_rud, name="transactions-rud"),
    path("transactions/summary/", transactions_summary, name="transactions-summary"),

    # Categories
    path("categories/", categories_list_create, name="categories-list-create"),
    path("categories/<int:pk>/", categories_rud, name="categories-rud"),
]
