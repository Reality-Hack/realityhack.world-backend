"""
ASGI config for event_server project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import re_path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'event_server.settings')

django_asgi_app = get_asgi_application()
from infrastructure import consumers

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(URLRouter([
            re_path(r"ws/lighthouses/$", consumers.LightHousesConsumer.as_asgi()),
            re_path(r"ws/lighthouse/(?P<table>\w+)/$", consumers.LightHouseByTableConsumer.as_asgi())
        ]))
    )
})
