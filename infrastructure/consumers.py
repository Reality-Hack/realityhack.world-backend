# chat/consumers.py
import json
from datetime import datetime

import django.db.utils
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q

from infrastructure.models import (LightHouse, MentorHelpRequest,
                                   MentorRequestStatus, Table, Team)
from infrastructure.serializers import LightHouseSerializer


class LightHouseByTableConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.table = self.scope["url_route"]["kwargs"]["table"]
        self.room_group_name = f"lighthouse_{self.table}"
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name
        )
        await self.accept()

        # TODO: .get() instead ?
        lighthouse = await LightHouse.objects.filter(table__number=self.table).afirst()
        
        table_hash = {
            "table": self.table,
            "ip_address": lighthouse.ip_address,
            "mentor_requested": lighthouse.mentor_requested,
            "announcement_pending": lighthouse.announcement_pending
        }
        
        serializer = LightHouseSerializer(table_hash)
        
        await self.send(text_data=json.dumps(serializer.data))

    @database_sync_to_async
    def set_lighthouse_status(self, text_data_dict):
        try:
            lighthouse = LightHouse.objects.get(table__number=self.scope["url_route"]["kwargs"]["table"])
            if text_data_dict.get("mentor_requested") == MentorRequestStatus.RESOLVED.value:
                lighthouse.mentor_requested = MentorRequestStatus.RESOLVED.value
            if text_data_dict.get("ip_address"):
                lighthouse.ip_address = text_data_dict.get("ip_address")
            lighthouse.save()
        except (LightHouse.DoesNotExist, django.db.utils.DataError, django.db.utils.IntegrityError, TypeError, json.decoder.JSONDecodeError) as error:
            pass

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name, self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get("message")
            # Send message to room group
            if not message:
                try:
                    text_data_dict = text_data_json
                    await self.set_lighthouse_status(text_data_dict)
                    return
                except json.decoder.JSONDecodeError as error:
                    message = {"type": "chat.message", "message": {"error": str(error), "original_message": message}}
            await self.channel_layer.group_send(
                self.room_group_name, message
            )
        except (json.JSONDecodeError) as error:
            pass

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]
        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))


class LightHousesConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_group_name = f"lighthouses"
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name, self.channel_name
        )
        await self.accept()

        lighthouses = []

        async for lighthouse in LightHouse.objects.all():
            table = await self.get_table(lighthouse)
            lighthouses.append(
                {
                    # "id": lighthouse.id,
                    "table": table.number,
                    "ip_address": lighthouse.ip_address,
                    "mentor_requested": lighthouse.mentor_requested,
                    "announcement_pending": lighthouse.announcement_pending
                }
            )
        serializer = LightHouseSerializer(lighthouses, many=True)
        await self.send(text_data=json.dumps(serializer.data))

    @database_sync_to_async
    def get_table(self, lighthouse):
        return lighthouse.table

    def get_lighthouses_by_table_number(self, table_numbers):
        all_tables = {table.number: table for table in Table.objects.all()}
        table_ids = [all_tables[table_number].id for table_number in table_numbers if table_number in all_tables]
        lighthouses = [lighthouse for lighthouse in LightHouse.objects.filter(table__pk__in=table_ids)]
        return lighthouses

    def set_announcement_status(self, lighthouse, status):
        lighthouse.announcement_pending = status
        lighthouse.save()

    def set_mentor_status(self, lighthouse, status):
        team = Team.objects.get(table=lighthouse.table)
        try:
            mentor_help_request = MentorHelpRequest.objects.filter(team=team).order_by("-created_at")[0]
            if mentor_help_request == MentorRequestStatus.RESOLVED and status == MentorRequestStatus.REQUESTED:
                MentorHelpRequest(team=team).save()  # create an empty MentorHelpRequest
            else:
                mentor_help_request.status = status
                mentor_help_request.save()
        except IndexError as error:
            if status == MentorRequestStatus.REQUESTED:
                if MentorHelpRequest.objects.filter(~Q(status=MentorRequestStatus.RESOLVED.value)).count() == 0:
                    return  # Do not accidentally create extra requests if there are other unfinished ones
                MentorHelpRequest(team=team).save()  # create an empty MentorHelpRequest

    @database_sync_to_async
    def handle_received_message(self, text_data_dict):
        lighthouses = self.get_lighthouses_by_table_number(text_data_dict.get("tables", []))
        for lighthouse in lighthouses:
            if text_data_dict.get("type") == LightHouse.MessageType.ANNOUNCEMENT.value:
                if text_data_dict.get("status") == LightHouse.AnnouncementStatus.RESOLVE.value:
                    self.set_announcement_status(lighthouse, LightHouse.AnnouncementStatus.RESOLVE.value)
                # elif text_data_dict.get("status") == LightHouse.AnnouncementStatus.ALERT.value:
                    # self.set_announcement_status(lighthouse, LightHouse.AnnouncementStatus.ALERT.value)
                elif text_data_dict.get("status") == LightHouse.AnnouncementStatus.SEND.value:
                    self.set_announcement_status(lighthouse, LightHouse.AnnouncementStatus.SEND.value)
            elif text_data_dict.get("type") == LightHouse.MessageType.MENTOR_REQUEST.value:
                if text_data_dict.get("status") == MentorRequestStatus.REQUESTED.value:
                    self.set_mentor_status(lighthouse, MentorRequestStatus.REQUESTED.value)
                elif text_data_dict.get("status") == MentorRequestStatus.ACKNOWLEDGED.value:
                    self.set_mentor_status(lighthouse, MentorRequestStatus.ACKNOWLEDGED)
                elif text_data_dict.get("status") == MentorRequestStatus.EN_ROUTE.value:
                    self.set_mentor_status(lighthouse, MentorRequestStatus.EN_ROUTE)
                elif text_data_dict.get("status") == MentorRequestStatus.RESOLVED.value:
                    self.set_mentor_status(lighthouse, MentorRequestStatus.RESOLVED)

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            text_data_dict = json.loads(text_data)
            await self.handle_received_message(text_data_dict)
        except (json.JSONDecodeError) as error:
            pass

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))
