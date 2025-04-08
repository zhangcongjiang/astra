import uuid

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
    voice_style = models.CharField(max_length=36)  # 对应的pt音色种子文件
    spec = models.JSONField(default=dict, null=True, blank=True)


class SoundTags(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sound_id = models.UUIDField()
    tag_id = models.UUIDField()
