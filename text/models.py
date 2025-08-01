import uuid

from django.db import models


# Create your models here.
class Text(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=30, blank=False)
    publish = models.BooleanField(default=False)
    creator = models.CharField(max_length=36, blank=False)
    origin = models.CharField(max_length=36, default="用户创建")
    create_time = models.DateTimeField(auto_now_add=True)  # 时间


class Graph(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.TextField()
    creator = models.CharField(max_length=36, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
