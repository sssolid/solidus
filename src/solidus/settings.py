# src/solidus/settings.py

import os
from pathlib import Path
from decouple import config

SHELL_PLUS = "ipython"

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='your-secret-key-here-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0', cast=lambda v: [s.strip() for s in v.split(',')])

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
]

THIRD_PARTY_APPS = [
    'channels',
    'django_extensions',
    'widget_tweaks',
    'django_cleanup',
    'django_htmx',
    'taggit',
    'corsheaders',
    'rest_framework',
    'django_filters',
    'compressor'
]

LOCAL_APPS = [
    'accounts',  # Must be first due to custom User model
    'autocare_pcadb',
    'autocare_vcdb',
    'core',
    'products',
    'assets',
    'feeds',
    'audit',
    'api',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Add automotive-specific settings
VCDB_SETTINGS = {
    'ENABLE_IMPORT_EXPORT': True,
    'ENABLE_BULK_OPERATIONS': True,
    'MAX_COMPARISON_VEHICLES': 5,
    'DEFAULT_PAGINATION_SIZE': 25,
    'CACHE_TIMEOUT': 300,  # 5 minutes
    'ENABLE_STATISTICS_CACHING': True,
}

MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'audit.middleware.AuditMiddleware',
]

ROOT_URLCONF = 'solidus.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_context',
                'core.context_processors.navigation_context',
                'core.context_processors.ui_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'solidus.wsgi.application'
ASGI_APPLICATION = 'solidus.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='solidus'),
        'USER': config('DB_USER', default='solidus'),
        'PASSWORD': config('DB_PASSWORD', default='solidus_password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# Autocare Database Configuration
AUTOCARE_DB_NAME_PCADB=config('AUTOCARE_DB_NAME_PCADB', default='pcadb')
AUTOCARE_DB_NAME_QDB=config('AUTOCARE_DB_NAME_QDB', default='qdb')
AUTOCARE_DB_NAME_VCDB=config('AUTOCARE_DB_NAME_VCDB', default='vcdb')
AUTOCARE_DB_ROOT_PASSWORD=config('AUTOCARE_DB_ROOT_PASSWORD', 'AutoRootPass567890!')
AUTOCARE_DB_USER=config('AUTOCARE_DB_USER', 'autocare')
AUTOCARE_DB_PASSWORD=config('AUTOCARE_DB_PASSWORD', 'AutocarePass098765!')
AUTOCARE_DB_HOST=config('AUTOCARE_DB_HOST', 'localhost')
AUTOCARE_DB_PORT=config('AUTOCARE_DB_PORT', 3306)

# Redis Configuration
REDIS_HOST = config('REDIS_HOST', default='localhost')
REDIS_PORT = config('REDIS_PORT', default=6379, cast=int)
REDIS_PASSWORD = config('REDIS_PASSWORD', default='')

REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}" if REDIS_PASSWORD else f"redis://{REDIS_HOST}:{REDIS_PORT}"

# Channels Configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [REDIS_URL],
        },
    },
}

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"{REDIS_URL}/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

COMPRESS_ENABLED = not DEBUG  # Disable compression in development
COMPRESS_OFFLINE = True  # Enables offline compression for production
COMPRESS_CSS_HASHING_METHOD = 'content'  # This ensures CSS is hashed correctly
COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']
COMPRESS_CSS_FILTERS = ['compressor.filters.cssmin.CSSMinFilter']

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'solidus': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'autocare_vcdb': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        }
    },
}

# Create logs directory
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Email Configuration
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend'
)
EMAIL_HOST = config('EMAIL_HOST', default='localhost')
EMAIL_PORT = config('EMAIL_PORT', default=1025, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@solidus.local')

# Security Settings
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# CORS settings
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# File Upload Settings
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 100  # 100MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 25   # 25MB

# Taggit Settings
TAGGIT_CASE_INSENSITIVE = True

# Django Extensions
GRAPH_MODELS = {
    'all_applications': True,
    'group_models': True,
}