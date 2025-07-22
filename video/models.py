import uuid

from django.core.validators import MinValueValidator, MaxValueValidator, DecimalValidator
from django.db import models


# 生成视频的输入参数
class Parameters(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template_id = models.CharField(max_length=36, blank=False)
    data = models.JSONField(default=dict)
    update_time = models.DateTimeField(auto_now_add=True)
    create_time = models.DateTimeField(auto_now_add=True)
    creator = models.CharField(max_length=16, blank=True)


# 视频
class Video(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=36)
    creator = models.CharField(max_length=16)
    result = models.CharField(max_length=16,
                              choices=[('Process', '视频生成中'), ('Fail', '视频生成失败'), ('Success', '生成成功')])
    process = models.FloatField(validators=[
        MinValueValidator(0.0),
        MaxValueValidator(1.0),
        DecimalValidator(max_digits=4, decimal_places=3)])

    param_id = models.UUIDField()
    create_time = models.DateTimeField(auto_now_add=True)
    spec = models.JSONField(default=dict, null=True, blank=True)


class VideoAsset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_name = models.TextField()
    origin = models.CharField(max_length=16, default="用户上传")
    creator = models.CharField(max_length=36, blank=True)
    duration = models.FloatField()
    orientation = models.CharField(max_length=16, choices=[('HORIZONTAL', '横版'), ('VERTICAL', '竖版')])
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True, blank=True)


class TemplateTags(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template_id = models.UUIDField(max_length=36)
    tag_id = models.UUIDField(max_length=36)
