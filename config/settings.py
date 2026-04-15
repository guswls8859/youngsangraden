from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this')

# 기상청 단기예보 API 키
KMA_API_KEY = os.getenv('KMA_API_KEY', '')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') + [
    'port-0-youngsangraden-mnr0z8y3c0b4fb14.sel3.cloudtype.app',
]

CSRF_TRUSTED_ORIGINS = [
    'https://port-0-youngsangraden-mnr0z8y3c0b4fb14.sel3.cloudtype.app',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'accounts',
    'reports',
    'parking',
    'info',
    'facilities',
    'sportsfield',
    'eventhouse',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    #  'default':{
    #     'ENGINE': 'django.db.backends.postgresql',
    #     'NAME': 'yongsan_garden',
    #     'USER': 'postgres',
    #     'PASSWORD': '1235gg',
    #     'HOST': 'localhost',
    #     'PORT': '5432',
    # }
    'default':{
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'yongsan_garden',
        'USER': 'root',
        'PASSWORD': '1235gg',
        'HOST': 'svc.sel3.cloudtype.app',
        'PORT': '30943',
    }
    # 'default': {
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': BASE_DIR / 'db.sqlite3',
    # }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'formatters': {
        'simple': {
            'format': '[{levelname}] {name} — {message}',
            'style': '{',
        },
    },
    'loggers': {
        'reports': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/menu/'
LOGOUT_REDIRECT_URL = '/accounts/login/'
