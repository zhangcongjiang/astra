import uuid

from django.db import models


# 生成视频的输入参数
class Parameters(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data = models.JSONField(default=dict)


# 视频
class Video(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=36)
    creator = models.CharField(max_length=16)
    result = models.BooleanField()
    param_id = models.UUIDField()
    create_time = models.DateTimeField(auto_now_add=True)
    spec = models.JSONField(default=dict, null=True, blank=True)


class VideoTags(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    video_id = models.UUIDField(max_length=36)
    tag_id = models.UUIDField(max_length=36)


class VideoProcess(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.CharField(max_length=16,
                               choices=[('PREPARATION', '素材准备中'), ('PROCESS', '视频生成中'), ('FAIL', '视频生成失败'), ('SUCCESS', '生成成功')])
    start_time = models.DateTimeField()
    update_time = models.DateTimeField(auto_now_add=True)
