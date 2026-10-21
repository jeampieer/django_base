from rest_framework import serializers


class ChangePasswordInputSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    current_password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)


class ChangePasswordOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    last_password_change = serializers.DateTimeField()


class ChangeRoleInputSerializer(serializers.Serializer):
    role = serializers.CharField(max_length=64)


class ChangeRoleOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    role = serializers.CharField()


class SetUserActiveInputSerializer(serializers.Serializer):
    pass


class SetUserActiveOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    is_active = serializers.BooleanField()
