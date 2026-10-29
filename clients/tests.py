"""Tests unitaires et d'intégration du service Clients."""
from io import StringIO
from unittest.mock import patch

import requests

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from . import messaging
from .models import Client

PASSWORD = "CafeKawa!2026"


@patch("clients.views.publish")
class AuthTests(APITestCase):
    def test_inscription_reussie_renvoie_des_jetons(self, mock_publish):
        data = {"email": "alice@test.fr", "password": PASSWORD, "nom": "Martin", "prenom": "Alice"}
        response = self.client.post(reverse("register"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertNotIn("password", response.data["client"])
        self.assertTrue(Client.objects.get(email="alice@test.fr").check_password(PASSWORD))
        mock_publish.assert_called_once()
        self.assertEqual(mock_publish.call_args[0][0], "client.created")

    def test_inscription_email_deja_utilise(self, mock_publish):
        Client.objects.create_user(email="alice@test.fr", password=PASSWORD, nom="M", prenom="A")
        data = {"email": "alice@test.fr", "password": PASSWORD, "nom": "Martin", "prenom": "Alice"}
        response = self.client.post(reverse("register"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inscription_mot_de_passe_trop_faible(self, mock_publish):
        data = {"email": "bob@test.fr", "password": "12345678", "nom": "B", "prenom": "B"}
        response = self.client.post(reverse("register"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_inscription_email_invalide(self, mock_publish):
        data = {"email": "pas-un-email", "password": PASSWORD, "nom": "B", "prenom": "B"}
        response = self.client.post(reverse("register"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_connexion_reussie_et_jeton_contient_is_staff(self, mock_publish):
        Client.objects.create_user(email="alice@test.fr", password=PASSWORD, nom="M", prenom="A")
        response = self.client.post(reverse("login"), {"email": "alice@test.fr", "password": PASSWORD})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken(response.data["access"])
        self.assertFalse(token["is_staff"])
        self.assertEqual(token["email"], "alice@test.fr")

    def test_connexion_mauvais_mot_de_passe(self, mock_publish):
        Client.objects.create_user(email="alice@test.fr", password=PASSWORD, nom="M", prenom="A")
        response = self.client.post(reverse("login"), {"email": "alice@test.fr", "password": "faux"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@patch("clients.views.publish")
class ClientCrudTests(APITestCase):
    def setUp(self):
        self.admin = Client.objects.create_superuser(email="admin@ptk.fr", password=PASSWORD, nom="Admin", prenom="A")
        self.alice = Client.objects.create_user(
            email="alice@test.fr", password=PASSWORD, nom="Martin", prenom="Alice", ville="Lyon",
        )
        self.bob = Client.objects.create_user(
            email="bob@test.fr", password=PASSWORD, nom="Durand", prenom="Bob",
            type_client="revendeur", societe="Bistrot du Coin", ville="Paris",
        )

    def detail(self, client):
        return reverse("client-detail", kwargs={"pk": client.id})

    def test_acces_refuse_sans_jeton(self, mock_publish):
        response = self.client.get(reverse("client-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_liste_reservee_aux_admins(self, mock_publish):
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.get(reverse("client-list")).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("client-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_recherche_et_filtre(self, mock_publish):
        self.client.force_authenticate(self.admin)
        response = self.client.get(reverse("client-list"), {"search": "bistrot"})
        self.assertEqual([c["email"] for c in response.data], ["bob@test.fr"])
        response = self.client.get(reverse("client-list"), {"type_client": "revendeur"})
        self.assertEqual(len(response.data), 1)

    def test_admin_cree_un_client(self, mock_publish):
        self.client.force_authenticate(self.admin)
        data = {"email": "carla@test.fr", "password": PASSWORD, "nom": "C", "prenom": "Carla"}
        response = self.client.post(reverse("client-list"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_publish.assert_called_with("client.created", mock_publish.call_args[0][1])

    def test_client_lit_sa_fiche_mais_pas_celle_des_autres(self, mock_publish):
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.get(self.detail(self.alice)).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(self.detail(self.bob)).status_code, status.HTTP_403_FORBIDDEN)

    def test_me(self, mock_publish):
        self.client.force_authenticate(self.bob)
        response = self.client.get(reverse("client-me"))
        self.assertEqual(response.data["email"], "bob@test.fr")

    def test_modification_publie_un_evenement(self, mock_publish):
        self.client.force_authenticate(self.alice)
        response = self.client.patch(self.detail(self.alice), {"ville": "Grenoble"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.ville, "Grenoble")
        self.assertEqual(mock_publish.call_args[0][0], "client.updated")

    def test_un_client_ne_peut_pas_se_donner_les_droits_admin(self, mock_publish):
        self.client.force_authenticate(self.alice)
        self.client.patch(self.detail(self.alice), {"is_staff": True, "is_active": False}, format="json")
        self.alice.refresh_from_db()
        self.assertFalse(self.alice.is_staff)
        self.assertTrue(self.alice.is_active)

    def test_suppression(self, mock_publish):
        self.client.force_authenticate(self.admin)
        response = self.client.delete(self.detail(self.bob))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Client.objects.filter(email="bob@test.fr").exists())
        self.assertEqual(mock_publish.call_args[0][0], "client.deleted")

    def test_client_inexistant(self, mock_publish):
        self.client.force_authenticate(self.admin)
        url = reverse("client-detail", kwargs={"pk": "00000000-0000-0000-0000-000000000000"})
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)


class HealthTests(APITestCase):
    def test_health(self):
        response = self.client.get("/health/")
        self.assertEqual(response.json(), {"status": "ok", "service": "client"})


RABBIT_ON = {"ENABLED": True, "HOST": "x", "PORT": 1, "USER": "g", "PASSWORD": "g", "EXCHANGE": "e"}


class MessagingTests(APITestCase):
    """Publication RabbitMQ : activée, désactivée, et en panne (tolérance aux pannes)."""

    @override_settings(RABBITMQ={"ENABLED": False})
    def test_publication_desactivee(self):
        self.assertFalse(messaging.publish("test.event", {"id": 1}))
        self.assertIsNone(messaging.start_consumer("q", {"a": print}))

    @override_settings(RABBITMQ=RABBIT_ON)
    @patch("clients.messaging._connection", side_effect=ConnectionError("RabbitMQ en panne"))
    def test_rabbitmq_en_panne_ne_bloque_pas(self, _):
        with self.assertLogs("clients.messaging", level="ERROR"):
            self.assertFalse(messaging.publish("test.event", {"id": 1}))

    @override_settings(RABBITMQ=RABBIT_ON)
    @patch("clients.messaging._connection")
    def test_publication_ok(self, mock_connection):
        self.assertTrue(messaging.publish("test.event", {"id": 1}))
        channel = mock_connection.return_value.channel.return_value
        body = channel.basic_publish.call_args.kwargs["body"]
        self.assertIn('"type": "test.event"', body)

    @override_settings(RABBITMQ=RABBIT_ON)
    @patch("clients.messaging.threading.Thread")
    def test_demarrage_du_consommateur(self, mock_thread):
        messaging.start_consumer("q", {"a.b": print})
        mock_thread.return_value.start.assert_called_once()

    @override_settings(RABBITMQ=RABBIT_ON)
    @patch("clients.messaging._connection")
    def test_consommateur_traite_et_acquitte(self, mock_connection):
        channel = mock_connection.return_value.channel.return_value
        received = []

        def fake_consume():
            on_message = channel.basic_consume.call_args.kwargs["on_message_callback"]
            method = type("M", (), {"routing_key": "a.b", "delivery_tag": 1})()
            on_message(channel, method, None, b'{"data": {"x": 1}}')
            on_message(channel, method, None, b"pas du json")
            raise KeyboardInterrupt  # sort de la boucle infinie pour le test

        channel.start_consuming.side_effect = fake_consume
        with self.assertRaises(KeyboardInterrupt), self.assertLogs("clients.messaging", level="ERROR"):
            messaging._consume_forever("q", {"a.b": received.append})
        self.assertEqual(received, [{"x": 1}])
        channel.basic_ack.assert_called_once_with(delivery_tag=1)
        channel.basic_nack.assert_called_once_with(delivery_tag=1, requeue=False)


class ImportCrmTests(APITestCase):
    """Reprise des données de l'ancien CRM (API mockée simulée)."""

    CRM_DATA = [
        {"id": "1", "username": "Jean.Dupont", "profile": {"firstName": "Jean", "lastName": "Dupont"},
         "address": {"postalCode": "69001", "city": "Lyon"}, "company": {"companyName": "Café Lumière"},
         "orders": [{"id": "1"}]},
        {"id": "2", "name": "Martin", "address": {}, "company": {}},
    ]

    @patch("clients.management.commands.import_crm.requests.get")
    def test_import_puis_reimport_sans_doublon(self, mock_get):
        from django.core.management import call_command
        mock_get.return_value.json.return_value = self.CRM_DATA
        call_command("import_crm", stdout=StringIO())
        jean = Client.objects.get(email="jean.dupont@import.payetonkawa.fr")
        self.assertEqual((jean.nom, jean.ville, jean.type_client), ("Dupont", "Lyon", "professionnel"))
        self.assertFalse(jean.has_usable_password())
        self.assertEqual(Client.objects.get(email="client2@import.payetonkawa.fr").type_client, "particulier")
        out = StringIO()
        call_command("import_crm", stdout=out)
        self.assertIn("0 client(s) créé(s), 2 mis à jour", out.getvalue())
        self.assertEqual(Client.objects.count(), 2)

    @patch("clients.management.commands.import_crm.requests.get", side_effect=requests.ConnectionError())
    def test_crm_injoignable(self, _):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command("import_crm", stdout=StringIO())


class ModelTests(APITestCase):
    def test_creation_sans_email_refusee(self):
        with self.assertRaises(ValueError):
            Client.objects.create_user(email="", password=PASSWORD)

    def test_affichage(self):
        client = Client(email="a@b.fr", nom="Martin", prenom="Alice")
        self.assertEqual(str(client), "Alice Martin (a@b.fr)")
