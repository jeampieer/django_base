from rest_framework import serializers

from applications.users.models import User
from applications.users.policies import PROFILE_FIELDS


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = PROFILE_FIELDS
        read_only_fields = PROFILE_FIELDS


class UserDetailSerializer(UserSerializer):
    """Salida de perfil; no expone hashes, privilegios técnicos ni contadores de bloqueo."""


class CreateUserInputSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    role = serializers.CharField(max_length=64, required=False)


class CreateUserOutputSerializer(UserDetailSerializer):
    pass


class UpdateUserInputSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)


class UpdateUserOutputSerializer(UserDetailSerializer):
    pass
