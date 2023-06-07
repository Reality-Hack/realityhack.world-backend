# chat/consumers.py
import json

from channels.generic.websocket import AsyncWebsocketConsumer

ANNOUNCEMENT = "ANNOUNCEMENT"
POSTED = "POSTED"
ACKNOWLEDGED = "ACKNOWLEDGED"


class RealityKitByTableConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.table = self.scope["url_route"]["kwargs"]["table"]
        self.channel_name = self.table
        self.room_group_name = "realitykits_group"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name, {"type": ANNOUNCEMENT, "message": message}
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))


class RealityKitsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.channel_name = "realitykits"
        self.room_group_name = "realitykits_group"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name, {"type": ANNOUNCEMENT, "message": message}
        )

        if text_data_json.get("type") == ANNOUNCEMENT and text_data_json.get("message") == ACKNOWLEDGED:
            pass
        else:
            await self.send(text_data=json.dumps({"type": ANNOUNCEMENT, "message": POSTED}))

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))