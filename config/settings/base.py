"""
Base settings to build other settings files upon.
"""

from collections import OrderedDict
from datetime import time, timedelta
from pathlib import Path

import environ
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
# ai_risiko/
APPS_DIR = BASE_DIR / "ai_risiko"
env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(BASE_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "Asia/Jakarta"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
# LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(BASE_DIR / "locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
# postgis geodjango dependencies
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"
# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",  # Handy template tags
    "filebrowser",
    "django.contrib.admin",
    "django.forms",
    "django.contrib.gis",  # postgis geodjango dependencies
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap3",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_celery_beat",
    "rest_framework",
    "rest_framework_gis",
    "rest_framework.authtoken",
    "corsheaders",
    "drf_spectacular",
    "django_filters",
    "leaflet",
    "related_admin",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "django_recaptcha",  # 202606
    "constance",  # 202609
]

LOCAL_APPS = [
    "ai_risiko.users",
    # Your stuff: custom apps go here
    "ai_risiko.airisiko",
    "ai_risiko.administrasiwilayah",
    "ai_risiko.dashboard",
    "ai_risiko.newdashboard",
    "ai_risiko.post",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "ai_risiko.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "users:redirect"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "django.middleware.gzip.GZipMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(BASE_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(APPS_DIR / "static")]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#dirs
        "DIRS": [str(APPS_DIR / "templates")],
        # https://docs.djangoproject.com/en/dev/ref/settings/#app-dirs
        "APP_DIRS": True,
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "constance.context_processors.config",  # 202609
                "ai_risiko.users.context_processors.allauth_settings",
                "ai_risiko.airisiko.context_processors.ai_risiko_last_updated",  # 202609
            ],
        },
    }
]

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options
X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL.
ADMIN_URL = "admin/"
# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [("""Admin AI Risiko""", "ai.risiko.dev@gmail.com")]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    # https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-timezone
    CELERY_TIMEZONE = TIME_ZONE
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-broker_url
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-result_backend
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-extended
CELERY_RESULT_EXTENDED = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-backend-always-retry
# https://github.com/celery/celery/pull/6122
CELERY_RESULT_BACKEND_ALWAYS_RETRY = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-backend-max-retries
CELERY_RESULT_BACKEND_MAX_RETRIES = 10
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-accept_content
CELERY_ACCEPT_CONTENT = ["json"]
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-task_serializer
CELERY_TASK_SERIALIZER = "json"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std:setting-result_serializer
CELERY_RESULT_SERIALIZER = "json"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_TIME_LIMIT = 5 * 60
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-soft-time-limit
# TODO: set to whatever value is adequate in your circumstances
CELERY_TASK_SOFT_TIME_LIMIT = 60
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#beat-scheduler
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#worker-send-task-events
CELERY_WORKER_SEND_TASK_EVENTS = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-task_send_sent_event
CELERY_TASK_SEND_SENT_EVENT = True
# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_AUTHENTICATION_METHOD = "username"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_REQUIRED = True
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_ADAPTER = "ai_risiko.users.adapters.AccountAdapter"
# https://django-allauth.readthedocs.io/en/latest/forms.html
ACCOUNT_FORMS = {
    "signup": "ai_risiko.users.forms.UserSignupForm",
    # "login": "ai_risiko.users.forms.UserLoginForm",  # disable recaptcha on login form
    "reset_password": "ai_risiko.users.forms.UserResetPasswordForm",
}
# https://django-allauth.readthedocs.io/en/latest/configuration.html
SOCIALACCOUNT_ADAPTER = "ai_risiko.users.adapters.SocialAccountAdapter"
# https://django-allauth.readthedocs.io/en/latest/forms.html
SOCIALACCOUNT_FORMS = {"signup": "ai_risiko.users.forms.UserSocialSignupForm"}

# django-rest-framework
# -------------------------------------------------------------------------------
# django-rest-framework - https://www.django-rest-framework.org/api-guide/settings/
# 202609 rate limit API POST/DELETE requests to 1 per minute
post_delete_throttle_rate = "5/minute"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # "rest_framework.authentication.SessionAuthentication",  # disable session auth for dj-rest-auth with jwt
        # "rest_framework.authentication.TokenAuthentication",  # replaced by JWT authentication
        "dj_rest_auth.jwt_auth.JWTCookieAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "exposure_create": post_delete_throttle_rate,
        "exposure_delete": post_delete_throttle_rate,
        "eq_create": post_delete_throttle_rate,
        "eq_start": post_delete_throttle_rate,
        "eq_abort": post_delete_throttle_rate,
        "eq_remove": post_delete_throttle_rate,
        "eq_delete": post_delete_throttle_rate,
    }
}

# django-cors-headers - https://github.com/adamchainz/django-cors-headers#setup
# CORS_URLS_REGEX = r"^/api/.*$"

# By Default swagger ui is available only to admin user(s). You can change permission classes to change that
# See more configuration options at https://drf-spectacular.readthedocs.io/en/latest/settings.html#settings
SPECTACULAR_SETTINGS = {
    "TITLE": "AI Risiko API",
    "DESCRIPTION": "Documentation of AI Risiko API endpoints",
    "VERSION": "1.0.0",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
}
# Your stuff...
# ------------------------------------------------------------------------------
# add dj-rest-auth endpoints
CORS_URLS_REGEX = r"^/api/.*$|^/rest-auth/.*$"

# djangorestframework-simplejwt settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),  # default is 1 day
}

# configure dj-rest-auth to use djangorestframework-simplejwt
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_HTTPONLY": False,  # required to return refresh token to api client
    "JWT_AUTH_RETURN_EXPIRATION": True,
    "JWT_AUTH_COOKIE": "_auth",
    "JWT_AUTH_REFRESH_COOKIE": "_refresh",
}

EMAIL_SUBJECT_PREFIX = env(
    "DJANGO_EMAIL_SUBJECT_PREFIX",
    default="[AI Risiko] ",
)

# https://docs.djangoproject.com/en/4.1/ref/settings/#std-setting-USE_L10N
USE_l10N = True
LANGUAGES = [
    ("id", _("Indonesian")),
    ("en", _("English")),
]
LANGUAGE_CODE = "en"

# use separate queue for openquake calculation tasks since calc servers are limited!
CELERY_TASK_ROUTES = {
    "openquake_submit_calc_task": {"queue": "openquake"},
    "calculation_server_check_active_task": {"queue": "low"},
    "openquake_check_complete_calc_task": {"queue": "low"},
}

# set celery task time limit to 2 hours
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 60 * 2  # 7200s
CELERY_TASK_TIME_LIMIT = 60 * 60 * 2 + 5  # 7205s (kills celery task 5s later)

# max file upload size in megabytes
MAX_FILE_UPLOAD_MB = env(
    "MAX_FILE_UPLOAD_MB",
    default=100,
)

# requests settings
REQUESTS_CONNECTION_TIMEOUT = 60
# attempts to make before marking connection as inactive
REQUESTS_MAX_CONNECTION_TRIES = 6
# time in seconds to wait between connection tries
REQUESTS_SLEEP_TIME = 10

# openquake instance details
OPENQUAKE_BASE_URL = env(
    "OPENQUAKE_BASE_URL",
    default="http://localhost:8800",
)
OPENQUAKE_ADMIN_LOGIN = env(
    "OPENQUAKE_ADMIN_LOGIN",
    default="admin",
)
OPENQUAKE_ADMIN_PASSWORD = env(
    "OPENQUAKE_ADMIN_PASSWORD",
    default="admin",
)

# valid time period for creating openquake jobs (for non superuser)
OPENQUAKE_JOB_PERIOD_ENABLE = env(
    "OPENQUAKE_JOB_PERIOD_ENABLE",
    default=False,
)
OPENQUAKE_JOB_PERIOD_START_HOUR = env(
    "OPENQUAKE_JOB_PERIOD_START_HOUR",
    default=7,
)
OPENQUAKE_JOB_PERIOD_END_HOUR = env(
    "OPENQUAKE_JOB_PERIOD_END_HOUR",
    default=18,
)
OPENQUAKE_JOB_PERIOD_START = time(
    hour=OPENQUAKE_JOB_PERIOD_START_HOUR, minute=0, second=0
)
OPENQUAKE_JOB_PERIOD_END = time(hour=OPENQUAKE_JOB_PERIOD_END_HOUR, minute=0, second=0)

# openquake web api docs https://github.com/gem/oq-engine/blob/master/doc/web-api.md
OPENQUAKE_LOGIN_ENDPOINT = "/accounts/ajax_login/"
OPENQUAKE_CALC_RUN_ENDPOINT = "/v1/calc/run"
OPENQUAKE_JOB_ABORT_ENDPOINT = "/v1/calc/{}/abort"  # job_id
OPENQUAKE_JOB_REMOVE_ENDPOINT = "/v1/calc/{}/remove"  # job_id
OPENQUAKE_JOB_STATUS_ENDPOINT = "/v1/calc/{}/status"  # job_id
OPENQUAKE_JOB_LOG_ENDPOINT = "/v1/calc/{}/log/0:"  # job_id
OPENQUAKE_JOB_TRACEBACK_ENDPOINT = "/v1/calc/{}/traceback"  # job_id
OPENQUAKE_JOB_RESULTS_ENDPOINT = "/v1/calc/{}/results"  # job_id
OPENQUAKE_JOB_RESULTS_DATASTORE_ENDPOINT = "/v1/calc/{}/datastore"  # job_id
OPENQUAKE_JOB_RESULTS_OUTPUT_ENDPOINT = (
    "/v1/calc/result/{}?export_type={}"  # result_id + type
)
OPENQUAKE_JOB_STATUS_INTERVAL = 10  # interval in seconds between checking job status
OPENQUAKE_JOB_STATUS_MAX_ERRORS = (
    10  # max errors checking job status before aborting job
)

# aws iam user for managing ec2 resources
EC2_AWS_REGION = env(
    "EC2_AWS_REGION",
    default=None,
)
EC2_AWS_ACCESS_KEY_ID = env(
    "EC2_AWS_ACCESS_KEY_ID",
    default=None,
)
EC2_AWS_SECRET_ACCESS_KEY = env(
    "EC2_AWS_SECRET_ACCESS_KEY",
    default=None,
)

# 202606 django-recaptcha
RECAPTCHA_PUBLIC_KEY = env("RECAPTCHA_PUBLIC_KEY")
RECAPTCHA_PRIVATE_KEY = env("RECAPTCHA_PRIVATE_KEY")
RECAPTCHA_REQUIRED_SCORE = 0.85

# 202608 fix osm basemap
LEAFLET_CONFIG = {
    "TILES": [
        (
            "OSM",
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                "attribution": '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                "referrerPolicy": "strict-origin-when-cross-origin",
            },
        )
    ]
}

# 202609 extra fix for osm basemap
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# 202609 use django-constance to store dynamic app config variables in redis
CONSTANCE_REDIS_CONNECTION = env("REDIS_URL", default="redis://redis:6379/0")

CONSTANCE_CONFIG = OrderedDict([
    ("OPENQUAKE_JOB_PERIOD_ENABLE", (OPENQUAKE_JOB_PERIOD_ENABLE, _("Enable OpenQuake Job Period"), bool)),
    ("OPENQUAKE_JOB_PERIOD_START", (OPENQUAKE_JOB_PERIOD_START, _("Period Start Time for OpenQuake Jobs"), time)),
    ("OPENQUAKE_JOB_PERIOD_END", (OPENQUAKE_JOB_PERIOD_END, _("Period End Time for OpenQuake Jobs"), time)),
])

# always update this on each commit
AI_RISIKO_LAST_UPDATED = "20260918.01"
