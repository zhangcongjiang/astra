import uuid

from django.db import models


# Create your models here.
class Text(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=36, blank=False)
    publish = models.BooleanField(default=False)
    creator = models.UUIDField(max_length=36, blank=False)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    content = models.TextField()
