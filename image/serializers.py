from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


class ImageUploadSerializer(serializers.Serializer):
    files = serializers.FileField()
    category = serializers.ChoiceField(choices=['normal', 'background'])


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


class ImageUploadSerializer(serializers.Serializer):
    files = serializers.FileField()
    category = serializers.ChoiceField(choices=['normal', 'background'])


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


from django.contrib.auth.models import User
from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height', 'img_path', 'username', 'create_time', 'spec', 'category', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        image_tags = ImageTags.objects.filter(image_id=obj.id)
        tags = []
        for image_tag in image_tags:
            tag = Tag.objects.get(id=image_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


class ImageUploadSerializer(serializers.Serializer):
    files = serializers.FileField()
    category = serializers.ChoiceField(choices=['normal', 'background'])
