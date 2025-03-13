import uuid

from django.db import models


# Create your models here.

class Sound(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sound_path = models.TextField()
    creator = models.CharField(max_length=36)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True, blank=True)


class Speaker(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    voice_style = models.CharField(max_length=36)


class Bgm(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bgm_path = models.TextField()
    name = models.CharField(max_length=36)
    creator = models.CharField(max_length=36, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True)


class BgmTags(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bgm_id = models.UUIDField()
    tag_id = models.UUIDField()


class Effects(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=36)
    effect_path = models.TextField()
    creator = models.CharField(max_length=36, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
