# Create your models here.
import uuid

from django.db import models


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




class ImageTags(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image_id = models.UUIDField()
    tag_id = models.UUIDField()


class Effects(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag_id = models.UUIDField()
    name = models.CharField(max_length=36)
