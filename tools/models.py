import uuid

from django.db import models


# Create your models here.
class Tool(models.Model):
    CATEGORY_CHOICES = [
        ('text', '文本工具'),
        ('image', '图像工具'),
        ('sound', '音频工具'),
        ('video', '视频工具'),
        ('other', '其他工具')
    ]
    ORIGIN_CHOICES = [
        ('system', '系统内置'),
        ('user', '用户上传'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tool_name = models.TextField()
    logo_path = models.TextField()
    url = models.TextField()
    origin = models.CharField(blank=False, choices=ORIGIN_CHOICES, default='user')
    category = models.CharField(blank=False, choices=CATEGORY_CHOICES, default='other')
    creator = models.CharField(max_length=36, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True, blank=True)


class SystemConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField("配置键", max_length=100, unique=True)
    value = models.TextField("配置值")
    description = models.TextField("描述", blank=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
