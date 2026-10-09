from django.db import transaction
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .chat import career_reply
from .models import ChatExchange, User


class MessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000, allow_blank=False)


def exchange_data(exchange):
    return {
        "id": exchange.id,
        "message": exchange.message,
        "reply": exchange.reply,
        "actions": exchange.actions,
        "created_at": exchange.created_at.isoformat(),
    }


class ChatView(APIView):
    def get(self, request):
        exchanges = list(ChatExchange.objects.filter(user=request.user)[:50])
        return Response([exchange_data(exchange) for exchange in reversed(exchanges)])

    def post(self, request):
        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            answer = career_reply(user, serializer.validated_data["message"])
            exchange = ChatExchange.objects.create(
                user=user, message=serializer.validated_data["message"], **answer
            )
            keep = list(ChatExchange.objects.filter(user=user).values_list("id", flat=True)[:50])
            ChatExchange.objects.filter(user=user).exclude(id__in=keep).delete()
        return Response(exchange_data(exchange), status=201)

    def delete(self, request):
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            ChatExchange.objects.filter(user=request.user).delete()
        return Response(status=204)
