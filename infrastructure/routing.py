from django.urls import re_path

from infrastructure import consumers

websocket_urlpatterns = [
    re_path(r"ws/lighthouses/$", consumers.LightHousesConsumer.as_asgi()),
    re_path(r"ws/lighthouse/(?P<table>\w+)/$",
            consumers.LightHouseByTableConsumer.as_asgi()),
]
