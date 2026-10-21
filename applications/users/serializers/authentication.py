from rest_framework import serializers

from applications.users.serializers.user import UserDetailSerializer


class LoginInputSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class LoginOutputSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserDetailSerializer()


class RefreshInputSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True, trim_whitespace=False)


class RefreshOutputSerializer(serializers.Serializer):
    access = serializers.CharField()


class VerifyInputSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, trim_whitespace=False)


class VerifyOutputSerializer(serializers.Serializer):
    valid = serializers.BooleanField()


class LogoutInputSerializer(serializers.Serializer):
    pass


class LogoutOutputSerializer(serializers.Serializer):
    detail = serializers.CharField()
