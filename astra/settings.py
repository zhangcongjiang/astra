"""
Django settings for astra project.

Generated by 'django-admin startproject' using Django 5.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

LOG_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

IMG_PATH = os.path.join(MEDIA_ROOT, "images")
SOUND_PATH = os.path.join(MEDIA_ROOT, "sound")
MOVIE_PATH = os.path.join(MEDIA_ROOT, "videos")
BGM_PATH = os.path.join(MEDIA_ROOT, "bgm")
LOGO_PATH = os.path.join(MEDIA_ROOT, "logo")
BKG_PATH = os.path.join(MEDIA_ROOT, "bkg")
FONTS_PATH = os.path.join(MEDIA_ROOT, 'fonts')
EFFECT_PATH = os.path.join(MEDIA_ROOT, 'effect')

MEDIA_URL = '/media/'
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-vls7q-d5q)l$fi99)hq*a^y(=hahdsng0po&tegl&8bz6til)s'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["10.67.0.165", "127.0.0.1", "localhost", "10.67.0.92"]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'drf_yasg',
    'rest_framework',
    'rest_framework.authtoken',
    'image',
    'voice',
    'video',
    'tag'
]
SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': False,
    'DEFAULT_FIELD_INSPECTORS': [
        'drf_yasg.inspectors.CamelCaseJSONFilter',
        'drf_yasg.inspectors.InlineSerializerInspector',
        'drf_yasg.inspectors.RelatedFieldInspector',
        'drf_yasg.inspectors.ChoiceFieldInspector',
        'drf_yasg.inspectors.FileFieldInspector',
        'drf_yasg.inspectors.DictFieldInspector',
        'drf_yasg.inspectors.SimpleFieldInspector',
        'drf_yasg.inspectors.StringDefaultFieldInspector',
    ],
    'SECURITY_DEFINITIONS': {
        'Token': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'Enter the token in the format `Token <your_token>`'
        }
    }
}
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        # 或者 'rest_framework.authentication.SessionAuthentication',
    ),

    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'astra.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
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

WSGI_APPLICATION = 'astra.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
TIME_ZONE = 'Asia/Shanghai'
DATABASES = {
    'default': {
        'TIME_ZONE': TIME_ZONE,
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'options': '-c search_path=django,public'
        },
        'NAME': 'videos',
        'USER': 'postgres',
        'PASSWORD': 'nsf0cus.@123',
        'HOST': '39.98.165.125',  # 或者使用数据库服务器的IP地址
        'PORT': '12345'  # 默认PostgreSQL端口

    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'image_handler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'image.log'),
            'when': 'midnight',  # 每天午夜切换日志文件
            'interval': 1,  # 每天切换一次
            'backupCount': 7,  # 最多保留7天
            'formatter': 'verbose',
        },
        'voice_handler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'voice.log'),
            'when': 'midnight',  # 每天午夜切换日志文件
            'interval': 1,  # 每天切换一次
            'backupCount': 7,  # 最多保留7天
            'formatter': 'verbose',
        },
        'video_handler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'video.log'),
            'when': 'midnight',  # 每天午夜切换日志文件
            'interval': 1,  # 每天切换一次
            'backupCount': 7,  # 最多保留7天
            'formatter': 'verbose',
        },
        'tag_handler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'tag.log'),
            'when': 'midnight',  # 每天午夜切换日志文件
            'interval': 1,  # 每天切换一次
            'backupCount': 7,  # 最多保留7天
            'formatter': 'verbose',
        }
    },
    'loggers': {
        'image': {
            'handlers': ['image_handler'],
            'level': 'INFO',
            'propagate': True,
        },
        'voice': {
            'handlers': ['voice_handler'],
            'level': 'INFO',
            'propagate': True,
        },
        'videos': {
            'handlers': ['video_handler'],
            'level': 'INFO',
            'propagate': True,
        },
        'tag': {
            'handlers': ['tag_handler'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

FFMPEG_PATH = r"C:\ffmpeg-7.1.1-full_build\bin\ffmpeg.exe"
