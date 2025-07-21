from rest_framework import serializers
from .models import Asset, AssetInfo

class AssetInfoSerializer(serializers.ModelSerializer):
    """素材信息序列化器"""
    class Meta:
        model = AssetInfo
        fields = ['id', 'resource_id', 'asset_type', 'index']
        read_only_fields = ['id', 'index']

class AssetSerializer(serializers.ModelSerializer):
    """素材集序列化器"""
    class Meta:
        model = Asset
        fields = ['id', 'set_name', 'creator', 'create_time']
        read_only_fields = ['id', 'create_time']

class AssetDetailSerializer(serializers.ModelSerializer):
    """素材集详情序列化器"""
    assets = serializers.SerializerMethodField()
    asset_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Asset
        fields = ['id', 'set_name', 'creator', 'create_time', 'assets', 'asset_count']
        read_only_fields = ['id', 'create_time']
    
    def get_assets(self, obj):
        """获取素材集中的所有素材"""
        asset_infos = AssetInfo.objects.filter(set_id=str(obj.id)).order_by('index')
        return AssetInfoSerializer(asset_infos, many=True).data
    
    def get_asset_count(self, obj):
        """获取素材数量"""
        return AssetInfo.objects.filter(set_id=str(obj.id)).count()

class AssetCreateUpdateSerializer(serializers.ModelSerializer):
    """素材集创建和更新序列化器"""
    class Meta:
        model = Asset
        fields = ['set_name', 'creator']

class AssetInfoCreateSerializer(serializers.ModelSerializer):
    """素材信息创建序列化器"""
    class Meta:
        model = AssetInfo
        fields = ['set_id', 'resource_id', 'asset_type']