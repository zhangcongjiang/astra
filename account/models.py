import uuid

from django.db import models


class SystemSettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.CharField(max_length=36, blank=True)
    key = models.CharField(max_length=36, blank=False)
    value = models.JSONField(default=dict, null=True, blank=True)

class Account(models.Model):

    pass