from django.urls import re_path

from infrastructure import consumers

websocket_urlpatterns = [
    re_path(r"ws/realitykits/$", consumers.RealityKitsConsumer.as_asgi()),
    re_path(r"ws/realitykit/(?P<table>\w+)/$", consumers.RealityKitByTableConsumer.as_asgi()),
]