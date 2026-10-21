from typing import Any

from model_bakery import baker
import pytest

from applications.example.models import Entry, Label
from applications.example.selectors.label_statistics import labels_with_entry_counts

pytestmark = pytest.mark.django_db


def test_aggregation_filters_inactive_entries_and_labels(django_assert_num_queries: Any) -> None:
    label = baker.make(Label, name="Visible")
    baker.make(Entry, label=label, _quantity=2)
    baker.make(Entry, label=label, is_active=False)
    baker.make(Entry, label=baker.make(Label, is_active=False))
    baker.make(Label)
    with django_assert_num_queries(1):
        result = list(labels_with_entry_counts(minimum_entries=2))
    assert [(item.name, item.entry_count) for item in result] == [("Visible", 2)]
