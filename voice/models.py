import uuid

from django.core.validators import MinValueValidator, MaxValueValidator, DecimalValidator
from django.db import models


# Create your models here.

class Sound(models.Model):
    CATEGORY_CHOICES = [
        ('BGM', '背景音乐'),
        ('EFFECT', '特效音'),
        ('SOUND', '普通音频'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sound_path = models.TextField()
    name = models.CharField(blank=True)
    desc = models.TextField()
    category = models.CharField(blank=False, choices=CATEGORY_CHOICES, default='SOUND')
    creator = models.CharField(max_length=36)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True, blank=True)


class Speaker(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    language = models.CharField(max_length=16)
    emotion = models.CharField(max_length=16)
    speed = models.FloatField(validators=[
        MinValueValidator(0.0),
        MaxValueValidator(2.0),
        DecimalValidator(max_digits=4, decimal_places=2)  # 总共最多4位数字，其中小数部分最多2位
    ])
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True, blank=True)


class SpeakerEmotion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    speaker_id = models.CharField(max_length=36)
    language = models.CharField(max_length=16)
    emotion = models.CharField(max_length=16)


class SoundTags(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sound_id = models.UUIDField()
    tag_id = models.UUIDField()


class SpeakerTags(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    speaker_id = models.UUIDField()
    tag_id = models.UUIDField()
