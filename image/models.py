# Create your models here.
import uuid
import os
import logging

from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver


# Create your models here.

class Image(models.Model):
    CATEGORY_CHOICES = [
        ('normal', '普通图片'),
        ('background', '背景图片'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    img_name = models.TextField()
    img_path = models.TextField()
    width = models.IntegerField()
    height = models.IntegerField()
    origin = models.CharField(max_length=16, default="用户上传")
    category = models.CharField(blank=False, choices=CATEGORY_CHOICES, default='normal')
    creator = models.CharField(max_length=36, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True, blank=True)


# 定义模块级 logger，供信号处理器使用
logger = logging.getLogger("image")


@receiver(pre_delete, sender=Image)
def delete_image_file(sender, instance, **kwargs):
    """在删除 Image 记录前，删除对应的图片文件。兼容 QuerySet.bulk delete。"""
    try:
        base_path = instance.img_path
        file_path = os.path.join(base_path, instance.img_name) if base_path else None
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"删除图片文件成功: {file_path}")
    except Exception as e:
        logger.error(f"删除图片文件失败: {e}")


class ImageTags(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image_id = models.UUIDField()
    tag_id = models.UUIDField()


class Effects(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag_id = models.UUIDField()
    name = models.CharField(max_length=36)
