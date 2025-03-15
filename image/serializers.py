from rest_framework import serializers

from image.models import Image, ImageTags
from tag.serializers import TagSerializer


class ImageTagsSerializer(serializers.ModelSerializer):
    tag = TagSerializer()

    class Meta:
        model = ImageTags
        fields = '__all__'


class ImageSerializer(serializers.ModelSerializer):
    tags = ImageTagsSerializer(source='tags', many=True, read_only=True)

    class Meta:
        model = Image
        fields = '__all__'


class BindTagsSerializer(serializers.Serializer):
    image_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())
