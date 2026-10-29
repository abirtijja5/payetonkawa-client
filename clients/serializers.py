"""Conversion Client <-> JSON et règles de validation."""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Client

PUBLIC_FIELDS = [
    "id", "email", "nom", "prenom", "telephone", "type_client", "societe",
    "adresse", "code_postal", "ville", "is_active", "created_at", "updated_at",
]


class ClientSerializer(serializers.ModelSerializer):
    """Lecture / modification d'un client (le mot de passe n'est jamais renvoyé)."""

    class Meta:
        model = Client
        fields = PUBLIC_FIELDS
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]


class ClientCreateSerializer(ClientSerializer):
    """Création d'un client : mot de passe obligatoire et contrôlé."""

    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})

    class Meta(ClientSerializer.Meta):
        fields = PUBLIC_FIELDS + ["password"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Client.objects.create_user(password=password, **validated_data)


class TokenSerializer(TokenObtainPairSerializer):
    """Ajoute au jeton JWT les informations utiles aux autres services."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["is_staff"] = user.is_staff
        token["type_client"] = user.type_client
        return token
