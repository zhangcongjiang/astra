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
    tool_logo_path = models.TextField()
    origin = models.CharField(blank=False, choices=ORIGIN_CHOICES, default='other')
    category = models.CharField(blank=False, choices=CATEGORY_CHOICES, default='other')
    creator = models.CharField(max_length=36, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True, blank=True)
