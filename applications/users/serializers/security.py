from rest_framework import serializers

from applications.users.models import SecurityEvent, UserSession


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = ("id", "user", "attempted_username", "status", "failure_reason", "ip_address", "login_at", "logout_at")
        read_only_fields = fields


class SecurityEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True, allow_null=True)
    target_username = serializers.CharField(source="target_user.username", read_only=True, allow_null=True)

    class Meta:
        model = SecurityEvent
        fields = ("id", "action", "actor", "actor_username", "target_user", "target_username", "created", "extra")
        read_only_fields = fields
