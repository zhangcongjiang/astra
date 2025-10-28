import uuid

from django.core.validators import MinValueValidator, MaxValueValidator, DecimalValidator
from django.db import models


# Create your models here.

class Sound(models.Model):
    CATEGORY_CHOICES = [
        ('BGM', 'BGM'),
        ('EFFECT', '特效音'),
        ('MUSIC', '音乐'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sound_path = models.TextField()
    name = models.CharField(blank=True)
    singer = models.CharField(max_length=36, blank=True)
    desc = models.TextField()

    category = models.CharField(blank=False, choices=CATEGORY_CHOICES, default='SOUND')
    creator = models.CharField(max_length=36)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True, blank=True)


class Tts(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    format = models.CharField(blank=True)
    duration = models.FloatField()
    txt = models.TextField()
    speaker_id = models.CharField(max_length=36)
    video_id = models.CharField(max_length=36, blank=True)
    creator = models.CharField(max_length=36)
    create_time = models.DateTimeField(auto_now_add=True)


class Speaker(models.Model):
    ORIGIN_CHOICES = [
        ('INDEX_TTS', 'INDEX-TTS'),
        ('EDGE_TTS', 'EDGE-TTS'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    origin = models.CharField(blank=False, choices=ORIGIN_CHOICES, default='INDEX_TTS')
    creator = models.CharField(max_length=36)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True, blank=True)


class SoundTags(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sound_id = models.UUIDField()
    tag_id = models.UUIDField()


class SpeakerTags(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    speaker_id = models.UUIDField()
    tag_id = models.UUIDField()
