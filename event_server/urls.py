"""
URL configuration for event_server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView, TokenVerifyView)

from infrastructure import views
from infrastructure.models import (Application, Attendee, Hardware,
                                   HardwareDevice, HelpDesk, Location, Project,
                                   Skill, SkillProficiency, Table, Team)

swagger_schema_view = get_schema_view(
   openapi.Info(
      title="Reality Hack event_server API",
      default_version='v1',
      description="The API and services running realityhack.world",
      terms_of_service="https://www.google.com/policies/terms/",
      #   contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="MIT License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

router = routers.DefaultRouter()
router.register(r'attendees', views.AttendeeViewSet)
router.register(r'skills', views.SkillViewSet)
router.register(r'locations', views.LocationViewSet)
router.register(r'tables', views.TableViewSet)
router.register(r'teams', views.TeamViewSet)
router.register(r'helpdesks', views.HelpDesksViewSet, basename='helpdesks')
router.register(r'request_mentor', views.MentorRequestViewSet, basename='requestmentor')
router.register(r'skillproficiencies', views.SkillProficiencyViewSet)
router.register(r'projects', views.ProjectViewSet)
router.register(r'groups', views.GroupViewSet)
router.register(r'hardware', views.HardwareViewSet)
router.register(r'hardwaredevices', views.HardwareDeviceViewSet)
router.register(r'hardwaredevicehistory', views.HardwareDeviceHistoryViewSet)
router.register(r'applications', views.ApplicationViewSet)

admin.site.register(Skill)
admin.site.register(Attendee)
admin.site.register(Location)
admin.site.register(Table)
admin.site.register(Team)
admin.site.register(HelpDesk)
admin.site.register(Project)
admin.site.register(SkillProficiency)
admin.site.register(Hardware)
admin.site.register(HardwareDevice)
admin.site.register(Application)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('schema/spectacular', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger<format>/', swagger_schema_view.without_ui(cache_timeout=0), name='swagger_schema_json'),
    path('schema/swagger/', swagger_schema_view.with_ui('swagger', cache_timeout=0), name='swagger_schema_swagger_ui'),
    path('schema/redoc/', swagger_schema_view.with_ui('redoc', cache_timeout=0), name='swagger_schema_redoc'),
]
