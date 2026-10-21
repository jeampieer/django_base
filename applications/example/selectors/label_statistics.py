from __future__ import annotations

from django.db.models import Count, Q, QuerySet

from applications.example.models import Label


def labels_with_entry_counts(*, minimum_entries: int = 1) -> QuerySet[Label]:
    """Cruza etiquetas y entradas activas en una única consulta agregada."""
    return (
        Label.objects.filter(is_active=True)
        .annotate(entry_count=Count("entries", filter=Q(entries__is_active=True)))
        .filter(entry_count__gte=minimum_entries)
        .order_by("name")
    )
