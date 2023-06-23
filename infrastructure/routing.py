from django.urls import re_path

from infrastructure import consumers

websocket_urlpatterns = [
    re_path(r"ws/HelpDesks/$", consumers.HelpDesksConsumer.as_asgi()),
    re_path(r"ws/HelpDesk/(?P<table>\w+)/$", consumers.HelpDeskByTableConsumer.as_asgi()),
]