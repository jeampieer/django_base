from rest_framework import serializers


class FinalizeEntryInputSerializer(serializers.Serializer):
    summary = serializers.CharField(max_length=250)


class FinalizeEntryOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    summary = serializers.CharField()
    finalized_at = serializers.DateTimeField()
