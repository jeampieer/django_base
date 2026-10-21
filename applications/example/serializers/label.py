from rest_framework import serializers

from applications.example.models import Label


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ("id", "name", "is_active", "created", "modified", "created_by", "updated_by")
        read_only_fields = ("id", "created", "modified", "created_by", "updated_by")
        # La unicidad la garantiza la BD; no se consulta desde el serializer.
        extra_kwargs = {"name": {"validators": []}}


class LabelDetailSerializer(LabelSerializer):
    """Sin relaciones que expandir: conserva la forma del serializer simple."""
