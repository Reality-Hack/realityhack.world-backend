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
from django.conf import settings
from django.conf.urls.static import static
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
                                   HardwareDevice, HardwareRequest, LightHouse,
                                   Location, MentorHelpRequest, Project, Skill,
                                   SkillProficiency, Table, Team, UploadedFile,
                                   Workshop, WorkshopAttendee)

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
router.register(r'attendees', views.AttendeeViewSet, basename="attendees")
router.register(r'discord', views.DiscordViewSet, basename="discord")
router.register(r'rsvps', views.AttendeeRSVPViewSet, basename="rsvps")
router.register(r'skills', views.SkillViewSet)
router.register(r'locations', views.LocationViewSet)
router.register(r'tables', views.TableViewSet)
router.register(r'teams', views.TeamViewSet)
router.register(r'lighthouses', views.LightHouseViewSet, basename='lighthouses')
router.register(r'mentorhelprequests', views.MentorHelpRequestViewSet, basename='mentorhelprequests')
router.register(r'mentorhelprequestshistory', views.MentorHelpRequestViewSetHistoryViewSet, basename='mentorhelprequestshistory')
router.register(r'skillproficiencies', views.SkillProficiencyViewSet)
router.register(r'projects', views.ProjectViewSet)
router.register(r'groups', views.GroupViewSet)
router.register(r'hardware', views.HardwareViewSet)
router.register(r'hardwaredevices', views.HardwareDeviceViewSet)
router.register(r'hardwarerequests', views.HardwareRequestsViewSet)
router.register(r'hardwaredevicehistory', views.HardwareDeviceHistoryViewSet)
router.register(r'applications', views.ApplicationViewSet)
router.register(r'uploaded_files', views.UploadedFileViewSet)
router.register(r'workshops', views.WorkshopViewSet)
router.register(r'workshopattendees', views.WorkshopAttendeeViewSet)

admin.site.register(Skill)
admin.site.register(Attendee)
admin.site.register(Location)
admin.site.register(Table)
admin.site.register(Team)
admin.site.register(LightHouse)
admin.site.register(Project)
admin.site.register(SkillProficiency)
admin.site.register(Hardware)
admin.site.register(HardwareDevice)
admin.site.register(HardwareRequest)
admin.site.register(Application)
admin.site.register(UploadedFile)
admin.site.register(Workshop)
admin.site.register(WorkshopAttendee)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('auth/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/spectacular/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger<format>/', swagger_schema_view.without_ui(cache_timeout=0), name='swagger_schema_json'),
    path('schema/swagger/', swagger_schema_view.with_ui('swagger', cache_timeout=0), name='swagger_schema_swagger_ui'),
    path('schema/redoc/', swagger_schema_view.with_ui('redoc', cache_timeout=0), name='swagger_schema_redoc'),
    path('me/', views.me, name='me'),
    path("lighthouse/", views.lighthouse, name="lighthouse"),
    path("lighthouse/<str:table_number>/", views.lighthouse_table, name="lighthouse_table"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
