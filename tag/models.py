import uuid

from django.db import models


# Create your models here.
class Tag(models.Model):
    tag_uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag_name = models.CharField(max_length=36)
    parent = models.CharField(max_length=36, blank=True)
    category = models.CharField(max_length=16, choices=[('VIDEO', '视频'), ('SOUND', '音频'), ('IMAGE', '图像')])
    creator = models.CharField(max_length=36, blank=True)
    origin = models.CharField(max_length=8, choices=[('INNER', '内置'), ('USER', '用户')], default='USER')
