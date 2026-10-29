"""Modèle de données du service Clients."""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class ClientManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Une adresse email est requise.")
        client = self.model(email=self.normalize_email(email), **extra_fields)
        client.set_password(password)  # mot de passe haché (jamais stocké en clair)
        client.save(using=self._db)
        return client

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class Client(AbstractBaseUser, PermissionsMixin):
    """Un client PayeTonKawa : particulier ou professionnel (restaurateur, revendeur)."""

    class Type(models.TextChoices):
        PARTICULIER = "particulier", "Particulier"
        PROFESSIONNEL = "professionnel", "Professionnel"
        REVENDEUR = "revendeur", "Revendeur"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=True)
    type_client = models.CharField(max_length=20, choices=Type.choices, default=Type.PARTICULIER)
    societe = models.CharField(max_length=150, blank=True)
    adresse = models.CharField(max_length=255, blank=True)
    code_postal = models.CharField(max_length=10, blank=True)
    ville = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nom", "prenom"]

    objects = ClientManager()

    class Meta:
        ordering = ["nom", "prenom"]

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.email})"
