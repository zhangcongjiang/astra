from django.db import models


# 生成视频的输入参数
class Parameters(models.Model):
    id = models.AutoField(primary_key=True)
    param_uuid = models.CharField(max_length=36)
    title = models.CharField(max_length=30)  # 标题
    voice = models.CharField(max_length=36, blank=True)  # 音色
    orientation = models.CharField(max_length=16, blank=True)
    template_uuid = models.CharField(max_length=36, blank=True)
    bkg = models.TextField(blank=True)  # 视频封面图
    beginning = models.JSONField(null=True)  # 视频开头
    content = models.JSONField(null=False)  # 制作视频的参数
    ending = models.JSONField(null=True)  # 视频结尾
    creator = models.CharField(max_length=16)
    create_time = models.DateTimeField(auto_now_add=True)


# 视频
class Video(models.Model):
    id = models.AutoField(primary_key=True)
    creator = models.CharField(max_length=16)
    result = models.BooleanField()
    video_uuid = models.CharField(max_length=36)
    param_uuid = models.CharField(max_length=36)
    create_time = models.DateTimeField(auto_now_add=True)
    spec = models.JSONField(default=dict, null=True)


class VideoTags(models.Model):
    id = models.AutoField(primary_key=True)
    video_uuid = models.CharField(max_length=36)
    tag_uuid = models.CharField(max_length=36)


class VideoProcess(models.Model):
    id = models.AutoField(primary_key=True)
    video_uuid = models.CharField(max_length=36)
    process = models.CharField(max_length=16, choices=[('VIDEO', '视频'), ('SOUND', '音频'), ('IMAGE', '图像')])
    start_time = models.DateTimeField()
    update_time = models.DateTimeField(auto_now_add=True)
