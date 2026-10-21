from rest_framework import serializers

from applications.example.models import Entry


class EntrySerializer(serializers.ModelSerializer):
    # Validación de formato sin lookup implícito de PrimaryKeyRelatedField.
    # La integridad referencial la garantiza la FK en la base de datos.
    label = serializers.UUIDField(source="label_id")

    class Meta:
        model = Entry
        fields = (
            "id", "title", "label", "status", "summary", "finalized_at", "is_active",
            "created", "modified", "created_by", "updated_by",
        )
        read_only_fields = (
            "id", "status", "summary", "finalized_at", "created", "modified", "created_by", "updated_by",
        )


class EntryDetailSerializer(EntrySerializer):
    """La representación de lectura expande la etiqueta precargada por la vista."""

    label_name = serializers.CharField(source="label.name", read_only=True)

    class Meta(EntrySerializer.Meta):
        fields = (*EntrySerializer.Meta.fields, "label_name")
