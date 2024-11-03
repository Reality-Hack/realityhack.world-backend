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
from environ import Env
env = Env()
env.read_env()

# SECURITY WARNING: don't run with DEBUG turned on in production!
SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="django-insecure-1234qwerty$#")
DEBUG = env.bool('DEBUG', default=False)
DEPLOYED = env('DEPLOYED', default=False)
# FRONTEND_URL = env("FRONTEND_URL", default="http://127.0.0.1:3000")

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    env("FRONTEND_DOMAIN", default="http://127.0.0.1:3000"), 
    env("KEYCLOAK_DOMAIN", default="http://127.0.0.1:3000")
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
   env("BACKEND_DOMAIN", default="http://127.0.0.1:8000")# For /admin pages
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_ALL_ORIGINS = False
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# LOGIN_REDIRECT_URL = env.str("LOGIN_REDIRECT_URL", default="http://localhost:3000")
# LOGOUT_REDIRECT_URL = env.str("LOGOUT_REDIRECT_URL", default="http://localhost:3000")

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
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django_keycloak_auth.middleware.KeycloakMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

LOCAL_DECODE = True

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
            'NAME': env("DJANGO_POSTGRESS_NAME", default="django"),
            'USER': env("DJANGO_POSTGRESS_USER", default="django"),
            'PASSWORD': env("DJANGO_POSTGRESS_PASS", default="password"),
            'HOST': env("POSTGRES_HOST", default="127.0.0.1"),
            'PORT': env("POSTGRES_PORT", default="5432"),
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
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter'
    ]
}

if not DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = ['rest_framework.renderers.JSONRenderer']

ASGI_APPLICATION = "infrastructure.routing.application"

if strtobool(os.getenv("DEPLOYED", "False")):
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [(env.str("REDIS_URL", default="redis://0.0.0.0:6379"))],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': "channels.layers.InMemoryChannelLayer"
        }
    }


# Daphne
ASGI_APPLICATION = "event_server.asgi.application"

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

if env("CLOUDFLARE_API_TOKEN", default="") != "":
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": env("CLOUDFLARE_ACCESS_KEY", default=""),
                "secret_key": env("CLOUDFLARE_SECRET_KEY", default=""),
                "endpoint_url": env("CLOUDFLARE_S3_ENDPOINT", default=""),
                "bucket_name": env("CLOUDFLARE_BUCKET_NAME", default=""),
                "region_name": "auto",
                "use_ssl": True,
                "signature_version": "s3v4",
            }
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

PHONENUMBER_DEFAULT_REGION = 'US'

SPECTACULAR_SETTINGS = {
    'REDOC_DIST': 'SIDECAR',
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
}
CSP_DEFAULT_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:")

# Option: CDN
CSP_DEFAULT_SRC = ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net")
CSP_IMG_SRC = ("'self'", "data:", "cdn.jsdelivr.net")

# Option: CDN
CSP_DEFAULT_SRC = ("'self'", "cdn.jsdelivr.net")

# required for both CDN and SIDECAR
CSP_WORKER_SRC = ("'self'", "blob:")
CSP_IMG_SRC = ("'self'", "data:", "cdn.redoc.ly")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "fonts.googleapis.com")
CSP_FONT_SRC = ("'self'", "fonts.gstatic.com")

CSP_DEFAULT_SRC = ("'self'", "http://localhost:3000", env("FRONTEND_DOMAIN", default="http://127.0.0.1:3000"))
CSP_CONNECT_SRC = ("'self'", "http://localhost:3000", env("FRONTEND_DOMAIN", default="http://127.0.0.1:3000"))

# Do not send emails during testing
if "test" not in sys.argv and "setup_test_data" not in sys.argv:
    EMAIL_HOST = os.getenv("EMAIL_HOST", "")
    EMAIL_PORT = os.getenv("EMAIL_PORT", "")
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "")

KEYCLOAK_EXEMPT_URIS = [
    'schema/swagger', 'schema/redoc', 'schema/spectacular',
    'applications/', 'uploaded_files/', 'attendees/', 'rsvps/', 'discord/'
]
KEYCLOAK_CONFIG = {
    'KEYCLOAK_SERVER_URL': os.getenv("KEYCLOAK_SERVER_URL", ""),
    'KEYCLOAK_REALM': os.getenv("KEYCLOAK_REALM", ""),
    'KEYCLOAK_CLIENT_ID': os.getenv("KEYCLOAK_CLIENT_ID", ""),
    'KEYCLOAK_CLIENT_SECRET_KEY': os.getenv("KEYCLOAK_CLIENT_SECRET_KEY", ""),
    "LOCAL_DECODE": LOCAL_DECODE
}


if "test" not in sys.argv:
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

ACCOUNT_USERNAME_REQUIRED = False
PHONENUMBER_DB_FORMAT = "RFC3966"
PHONENUMBER_DEFAULT_FORMAT = "RFC3966"

# might not be needed - this was when debugging keycloak on Fly
if strtobool(os.getenv("FLY_DEPLOYED", "False")):
    print("FLY_DEPLOYED is True")
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if strtobool(os.getenv("DEPLOYED", "False")):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379"),
        }
    }
