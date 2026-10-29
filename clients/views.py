"""Endpoints REST du service Clients."""
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .messaging import publish
from .models import Client
from .permissions import IsStaffOrSelf
from .serializers import ClientCreateSerializer, ClientSerializer, TokenSerializer


def client_event(client):
    return {
        "id": str(client.id), "email": client.email, "nom": client.nom,
        "prenom": client.prenom, "type_client": client.type_client,
    }


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ : inscription publique, renvoie directement les jetons."""

    serializer_class = ClientCreateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = serializer.save()
        publish("client.created", client_event(client))
        refresh = TokenSerializer.get_token(client)
        return Response(
            {
                "client": ClientSerializer(client).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=201,
        )


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ : email + mot de passe -> jetons JWT."""

    serializer_class = TokenSerializer


class ClientViewSet(viewsets.ModelViewSet):
    """
    CRUD des clients.
    - liste / création : administrateurs uniquement
    - lecture / modification / suppression : administrateur ou le client lui-même
    - recherche : ?search=dupont   tri : ?ordering=-created_at   filtre : ?type_client=revendeur
    """

    queryset = Client.objects.all()
    search_fields = ["nom", "prenom", "email", "societe", "ville"]
    ordering_fields = ["nom", "created_at"]

    def get_serializer_class(self):
        return ClientCreateSerializer if self.action == "create" else ClientSerializer

    def get_permissions(self):
        if self.action in ("list", "create"):
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated(), IsStaffOrSelf()]

    def get_queryset(self):
        queryset = super().get_queryset()
        type_client = self.request.query_params.get("type_client")
        if type_client:
            queryset = queryset.filter(type_client=type_client)
        return queryset

    def perform_create(self, serializer):
        client = serializer.save()
        publish("client.created", client_event(client))

    def perform_update(self, serializer):
        client = serializer.save()
        publish("client.updated", client_event(client))

    def perform_destroy(self, instance):
        data = client_event(instance)
        instance.delete()
        publish("client.deleted", data)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """GET /api/clients/me/ : la fiche du client connecté."""
        return Response(ClientSerializer(request.user).data)
