from django.contrib.auth.models import User
from rest_framework import serializers

from text.models import Graph
from video.models import VideoAsset
from .models import Asset, AssetInfo
from django.db.models import Count, Case, When
from image.models import Image
from voice.models import Sound


class AssetInfoSerializer(serializers.ModelSerializer):
    """素材信息序列化器"""

    class Meta:
        model = AssetInfo
        fields = ['id', 'resource_id', 'asset_type', 'index']
        read_only_fields = ['id', 'index']


class AssetInfoDetailSerializer(serializers.ModelSerializer):
    """素材信息详情序列化器"""
    resource_detail = serializers.SerializerMethodField()

    class Meta:
        model = AssetInfo
        fields = ['id', 'resource_id', 'asset_type', 'index', 'resource_detail']
        read_only_fields = ['id', 'index']

    def get_resource_detail(self, obj):
        """根据素材类型获取详细信息"""

        try:
            if obj.asset_type == 'image':
                image = Image.objects.get(id=obj.resource_id)
                return {
                    'id': image.id,
                    'name': image.img_name,
                    'url': "/media/images/" + image.img_name,
                    'width': image.width,
                    'height': image.height,
                    'format': image.spec.get('format', 'jpg'),
                    'create_time': image.create_time
                }
            elif obj.asset_type == 'text':
                graph = Graph.objects.get(id=obj.resource_id)
                return {
                    'id': graph.id,
                    'text': graph.text,
                    'creator': graph.creator,
                    'create_time': graph.create_time
                }
            elif obj.asset_type == 'video':
                video = VideoAsset.objects.get(id=obj.resource_id)
                return {
                    'id': video.id,
                    'name': video.asset_name,
                    'url': "/media/" + video.spec['file_path'],
                    'duration': video.spec.get('duration', 0),
                    'size': video.spec.get('size', 0),
                    'format': video.spec.get('format', 'mp4'),
                    'create_time': video.create_time
                }
            elif obj.asset_type == 'sound':
                voice = Sound.objects.get(id=obj.resource_id)
                return {
                    'id': voice.id,
                    'name': voice.name,
                    'singer': voice.singer,
                    'url': "/media/sound/" + voice.sound_path,
                    'duration': voice.spec.get('duration', 0),
                    'size': voice.spec.get('size', 0),
                    'format': voice.spec.get('format', "mp4"),
                    'create_time': voice.create_time
                }
        except Exception as e:
            return {'error': f'获取{obj.asset_type}详情失败: {str(e)}'}

        return None


class AssetSerializer(serializers.ModelSerializer):
    """素材集序列化器"""
    asset_count = serializers.SerializerMethodField()
    cover_img = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = ['id', 'set_name', 'username', 'create_time', 'asset_count', 'cover_img']
        read_only_fields = ['id', 'create_time']

    def get_asset_count(self, obj):
        """获取各类型素材数量"""
        counts = AssetInfo.objects.filter(set_id=str(obj.id)).count()
        return counts

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username

    def get_cover_img(self, obj):
        """获取素材集封面图片（index最小的图片素材）"""
        try:
            # 查找该素材集中index最小的图片素材
            first_image_asset = AssetInfo.objects.filter(
                set_id=str(obj.id),
                asset_type='image'
            ).order_by('index').first()

            if first_image_asset:
                # 获取图片详细信息
                from image.models import Image
                image = Image.objects.get(id=first_image_asset.resource_id)
                return "/media/images/" + image.img_name  # 假设图片路径为"/media/images/xxx.jpg"
            else:
                return None
        except Exception as e:
            return {'error': f'获取封面图片失败: {str(e)}'}


class AssetDetailSerializer(serializers.ModelSerializer):
    """素材集详情序列化器"""
    images = serializers.SerializerMethodField()
    texts = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()
    sounds = serializers.SerializerMethodField()
    asset_count = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = ['id', 'set_name', 'username', 'create_time', 'images', 'texts', 'videos', 'sounds', 'asset_count']
        read_only_fields = ['id', 'create_time']

    def get_images(self, obj):
        """获取图片素材"""
        asset_infos = AssetInfo.objects.filter(set_id=str(obj.id), asset_type='image').order_by('index')
        return AssetInfoDetailSerializer(asset_infos, many=True).data

    def get_texts(self, obj):
        """获取文本素材"""
        asset_infos = AssetInfo.objects.filter(set_id=str(obj.id), asset_type='text').order_by('index')
        return AssetInfoDetailSerializer(asset_infos, many=True).data

    def get_videos(self, obj):
        """获取视频素材"""
        asset_infos = AssetInfo.objects.filter(set_id=str(obj.id), asset_type='video').order_by('index')
        return AssetInfoDetailSerializer(asset_infos, many=True).data

    def get_sounds(self, obj):
        """获取音频素材"""
        asset_infos = AssetInfo.objects.filter(set_id=str(obj.id), asset_type='sound').order_by('index')
        return AssetInfoDetailSerializer(asset_infos, many=True).data

    def get_asset_count(self, obj):
        """获取各类型素材数量"""

        counts = AssetInfo.objects.filter(set_id=str(obj.id)).aggregate(
            image_count=Count(Case(When(asset_type='image', then=1))),
            text_count=Count(Case(When(asset_type='text', then=1))),
            video_count=Count(Case(When(asset_type='video', then=1))),
            sound_count=Count(Case(When(asset_type='sound', then=1))),
            total_count=Count('id')
        )
        return counts

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class AssetCreateUpdateSerializer(serializers.ModelSerializer):
    """素材集创建和更新序列化器"""

    class Meta:
        model = Asset
        fields = ['set_name', 'desc', 'creator']


class AssetUpdateSerializer(serializers.ModelSerializer):
    """素材集更新序列化器 - 只允许更新名称"""

    class Meta:
        model = Asset
        fields = ['set_name']

    def validate_set_name(self, value):
        """验证素材集名称"""
        if not value or not value.strip():
            raise serializers.ValidationError("素材集名称不能为空")
        if len(value.strip()) > 36:
            raise serializers.ValidationError("素材集名称不能超过36个字符")
        return value.strip()


class AssetInfoCreateSerializer(serializers.ModelSerializer):
    """素材信息创建序列化器"""

    class Meta:
        model = AssetInfo
        fields = ['set_id', 'resource_id', 'asset_type']
