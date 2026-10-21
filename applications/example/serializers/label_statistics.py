from rest_framework import serializers


class LabelStatisticsInputSerializer(serializers.Serializer):
    minimum_entries = serializers.IntegerField(min_value=0, default=1)


class LabelStatisticsOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    entry_count = serializers.IntegerField()
