from rest_framework import serializers

from image.models import Image, ImageTags
from tag.models import Tag


class ImageSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'img_name', 'width', 'height','img_path', 'creator', 'create_time', 'spec', 'category', 'tags']

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


class ImageBindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())
