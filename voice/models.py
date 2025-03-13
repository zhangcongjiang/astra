from django.db import models


# Create your models here.

class Sound(models.Model):
    id = models.BigAutoField(primary_key=True)
    sound_uuid = models.CharField(max_length=36)
    sound_path = models.TextField()
    creator = models.CharField(max_length=36)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True)


class Speaker(models.Model):
    id = models.BigAutoField(primary_key=True)
    speaker_uuid = models.CharField(max_length=36)
    name = models.TextField()
    voice_style = models.CharField(max_length=36)


class Bgm(models.Model):
    id = models.BigAutoField(primary_key=True)
    bgm_uuid = models.CharField(max_length=36)
    bgm_path = models.TextField()
    name = models.CharField(max_length=36)
    creator = models.CharField(max_length=36, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True)


class BgmTags(models.Model):
    id = models.BigAutoField(primary_key=True)
    bgm_uuid = models.CharField(max_length=36)
    tag_uuid = models.CharField(max_length=36)


class Effects(models.Model):
    id = models.BigAutoField(primary_key=True)
    tag_uuid = models.CharField(max_length=36)
    name = models.CharField(max_length=36)
    effect_path = models.TextField()
    creator = models.CharField(max_length=36, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
