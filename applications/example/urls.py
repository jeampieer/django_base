from django.urls import path

from .api_views.entry import EntryDetailView, EntryFilterView, EntryListView
from .api_views.finalize_entry import FinalizeEntryView
from .api_views.label import LabelDetailView, LabelFilterView, LabelListView
from .api_views.label_statistics import LabelStatisticsView

app_name = "example"
urlpatterns = [
    path("labels/", LabelListView.as_view(), name="label-list"),
    path("labels/filter/", LabelFilterView.as_view(), name="label-filter"),
    path("labels/statistics/", LabelStatisticsView.as_view(), name="label-statistics"),
    path("labels/<uuid:pk>/", LabelDetailView.as_view(), name="label-detail"),
    path("entries/", EntryListView.as_view(), name="entry-list"),
    path("entries/filter/", EntryFilterView.as_view(), name="entry-filter"),
    path("entries/<uuid:pk>/", EntryDetailView.as_view(), name="entry-detail"),
    path("entries/<uuid:pk>/finalize/", FinalizeEntryView.as_view(), name="entry-finalize"),
]
