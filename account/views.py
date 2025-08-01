from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from account.models import SystemSettings
from account.serializers import SystemSettingsSerializer
from common.response import error_response, ok_response


# Create your views here.
class SystemSettingsAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="系统设置内容更新",
        request_body=SystemSettingsSerializer,
        responses={
            0: "更新成功",
            1: "更新失败",
        },
    )
    def post(self, request):
        # 验证输入数据
        serializer = SystemSettingsSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("无效的输入")
        user_id = request.user.id
        key = serializer.validated_data['key']
        value = serializer.validated_data['value']
        try:
            settings = SystemSettings.objects.filter(user=user_id, key=key)
            if len(settings) != 1:
                return error_response("系统错误，请联系管理员")
            else:
                setting = settings[0]
                exist_values = setting.value
                for k, v in value:
                    exist_values[k] = v
                setting.value = exist_values
                setting.save()
            return ok_response("更新成功")
        except Exception:
            return error_response("系统错误，请联系管理员")


class SystemSettingsQueryView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="根据key查询系统设置",
        manual_parameters=[
            openapi.Parameter('key', openapi.IN_QUERY, description="系统设置key", type=openapi.TYPE_STRING),
        ],
        responses={200: SystemSettingsSerializer(many=False)}

    )
    def get(self, request):
        # 验证输入参数

        user_id = request.user.id
        key = request.query_params.get('key')

        try:
            # 查询用户的特定配置
            setting = SystemSettings.objects.filter(user=user_id, key=key).first()
            if setting:
                data = {
                    'key': setting.key,
                    'value': setting.value
                }
                return ok_response(data)
            else:
                setting = SystemSettings.objects.create(key=key, user=user_id, value={})
                return ok_response({
                    'key': key,
                    'value': setting.value
                })
        except Exception as e:
            return error_response("系统错误，请联系管理员")
