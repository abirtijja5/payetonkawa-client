"""
python manage.py import_crm
Reprise des clients de l'ancien CRM (API REST mockée fournie par PayeTonKawa).
Le champ "orders" de l'ancien modèle n'est volontairement pas repris :
les commandes appartiennent désormais au service Commandes.
"""
import os

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from clients.models import Client

DEFAULT_URL = "https://615f5fb4f7254d0017068109.mockapi.io/api/v1"


def map_customer(raw):
    """Transforme un client de l'ancien CRM vers le nouveau modèle."""
    profile = raw.get("profile") or {}
    address = raw.get("address") or {}
    company = (raw.get("company") or {}).get("companyName", "")
    username = raw.get("username") or f"client{raw.get('id')}"
    return {
        "email": (raw.get("email") or f"{username}@import.payetonkawa.fr").lower(),
        "nom": profile.get("lastName") or raw.get("lastName") or raw.get("name") or "Inconnu",
        "prenom": profile.get("firstName") or raw.get("firstName") or "",
        "code_postal": str(address.get("postalCode", ""))[:10],
        "ville": address.get("city", ""),
        "societe": company,
        "type_client": Client.Type.PROFESSIONNEL if company else Client.Type.PARTICULIER,
    }


class Command(BaseCommand):
    help = "Importe les clients de l'ancien CRM (sans doublon, par email)."

    def add_arguments(self, parser):
        parser.add_argument("--url", default=os.environ.get("CRM_API_URL", DEFAULT_URL))

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            response = requests.get(f"{options['url']}/customers", timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CommandError(f"CRM injoignable : {exc}")

        created = updated = 0
        for raw in response.json():
            data = map_customer(raw)
            client, is_new = Client.objects.update_or_create(email=data.pop("email"), defaults=data)
            if is_new:
                client.set_unusable_password()  # le client choisira son mot de passe
                client.save(update_fields=["password"])
                created += 1
            else:
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"{created} client(s) créé(s), {updated} mis à jour."))
