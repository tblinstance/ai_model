"""URL routes for transactions app."""

from django.urls import path

from .views import TopUpCreditsView, TransactionListView, TransactionSummaryView

urlpatterns = [
    path("", TransactionListView.as_view(), name="transaction-list"),
    path("summary/", TransactionSummaryView.as_view(), name="transaction-summary"),
    path("topup/", TopUpCreditsView.as_view(), name="transaction-topup"),
]

