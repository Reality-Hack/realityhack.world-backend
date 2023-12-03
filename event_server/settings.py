"""
Django settings for event_server project.

Generated by 'django-admin startproject' using Django 4.2.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import os
import sys
from datetime import timedelta
from distutils.util import strtobool
from pathlib import Path

import django
from dotenv import load_dotenv

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

load_dotenv()

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = strtobool(os.environ["DEBUG"])
DEPLOYED = strtobool(os.environ["DEPLOYED"])

CORS_ALLOWED_ORIGINS = [
    os.environ["FRONTEND_DOMAIN"]
]

CSRF_TRUSTED_ORIGINS = [
    os.environ["BACKEND_DOMAIN"]  # For /admin pages
]

CORS_ALLOW_ALL_ORIGINS = False
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True

LOGIN_REDIRECT_URL = "http://127.0.0.1:8080/realms/master/broker/codeberg/endpoint"
LOGOUT_REDIRECT_URL = "<URL path to redirect to after logout>"

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
if "test" in sys.argv:
    MEDIA_ROOT = f"{MEDIA_ROOT}/test"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!

ALLOWED_HOSTS = ['*']

AUTH_USER_MODEL = 'infrastructure.Attendee'

# Application definition

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'infrastructure',
    'channels',
    'drf_spectacular',
    'django_filters',
    'simple_history',
    'phonenumber_field',
    'drf_yasg',
    'corsheaders'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django_keycloak_auth.middleware.KeycloakMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

ROOT_URLCONF = 'event_server.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
if DEPLOYED or "makemigrations" in sys.argv:  # Not using a virtual env = is deployed
    DATABASES = {  # pragma: nocover
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'django',
            'USER': 'django',
            'PASSWORD': os.getenv("DJANGO_POSTGRESS_PASS"),
            'HOST': '127.0.0.1',
            'PORT': '5432',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',  # noqa: E501
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.DjangoModelPermissions',
    ),
        'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication'
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter'
    ]
}

# AUTHENTICATION_BACKENDS = []

ASGI_APPLICATION = "infrastructure.routing.application"
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': "channels.layers.InMemoryChannelLayer"
    }
}

# Daphne
ASGI_APPLICATION = "event_server.asgi.application"

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

PHONENUMBER_DEFAULT_REGION = 'US'

# Do not send emails during testing
if "test" not in sys.argv and "setup_test_data" not in sys.argv:
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = os.environ["EMAIL_PORT"]
    EMAIL_HOST_USER = os.environ["EMAIL_HOST_USER"]
    EMAIL_HOST_PASSWORD = os.environ["EMAIL_HOST_PASSWORD"]
    EMAIL_USE_SSL = os.environ["EMAIL_USE_SSL"]

KEYCLOAK_EXEMPT_URIS = [
    'schema/swagger', 'schema/redoc', 'schema/spectacular',
    'applications/', 'uploaded_files'
]
KEYCLOAK_CONFIG = {
    'KEYCLOAK_SERVER_URL': os.environ["KEYCLOAK_SERVER_URL"],
    'KEYCLOAK_REALM': os.environ["KEYCLOAK_REALM"],
    'KEYCLOAK_CLIENT_ID': os.environ["KEYCLOAK_CLIENT_ID"],
    'KEYCLOAK_CLIENT_SECRET_KEY': os.environ["KEYCLOAK_CLIENT_SECRET_KEY"]
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/request.log',
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 5,
            'encoding': 'utf-8',
            'formatter': 'verbose'
        },
    },
    'formatters': {
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] %(message)s (%(filename)s:%(lineno)s)',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
