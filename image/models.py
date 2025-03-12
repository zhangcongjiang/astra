# Create your models here.
from django.db import models


# Create your models here.

class Image(models.Model):
    id = models.AutoField(primary_key=True)
    image_uuid = models.CharField(max_length=36)
    img_path = models.TextField()
    creator = models.CharField(max_length=36)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True)


class ImageTags(models.Model):
    id = models.AutoField(primary_key=True)
    image_uuid = models.CharField(max_length=36)
    tag_uuid = models.CharField(max_length=36)


class Bkg(models.Model):
    id = models.AutoField(primary_key=True)
    bkg_uuid = models.CharField(max_length=36)
    name = models.CharField(max_length=36)
    img_path = models.TextField()
    creator = models.CharField(max_length=36, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True)


class BkgTags(models.Model):
    id = models.AutoField(primary_key=True)
    bkg_uuid = models.CharField(max_length=36)
    tag_uuid = models.CharField(max_length=36)


class Effects(models.Model):
    id = models.AutoField(primary_key=True)
    tag_uuid = models.CharField(max_length=36)
    name = models.CharField(max_length=36)
