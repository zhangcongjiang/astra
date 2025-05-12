import uuid

from django.db import models


# 生成视频的输入参数
class Parameters(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=30)  # 标题
    voice = models.CharField(max_length=36, blank=True)  # 音色
    orientation = models.CharField(max_length=16, blank=True)
    template_id = models.UUIDField()
    bkg = models.TextField(blank=True)  # 视频封面图
    beginning = models.JSONField(null=True)  # 视频开头
    content = models.JSONField(null=False)  # 制作视频的参数
    ending = models.JSONField(null=True)  # 视频结尾
    creator = models.CharField(max_length=16)
    create_time = models.DateTimeField(auto_now_add=True)


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
