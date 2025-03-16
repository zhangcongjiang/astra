import mimetypes
import os
import uuid

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

from astra.settings import EFFECT_PATH
from common.response import error_response, ok_response

from pydub import AudioSegment

from voice.models import Effects


class EffectUploadView(generics.CreateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        return None

    @swagger_auto_schema(
        operation_description="上传音频特效",
        manual_parameters=[
            openapi.Parameter(
                'file', openapi.IN_FORM, description="音频特效文件", type=openapi.TYPE_FILE, required=True
            ),
            openapi.Parameter(
                'name', openapi.IN_FORM, description="音频特效名称", type=openapi.TYPE_STRING, required=True
            ),
            openapi.Parameter(
                'desc', openapi.IN_FORM, description="描述信息", type=openapi.TYPE_STRING, required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="音频特效上传成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": "image_path",
                        "msg": "success"
                    }
                }
            )
        }
    )
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        name = request.data.get('name')
        desc = request.data.get('desc', '')
        if not file:
            return error_response("未提供音频特效")
        valid_mime_types = ['audio/wav', 'audio/mp3']
        mime_type, _ = mimetypes.guess_type(file.name)

        if mime_type not in valid_mime_types:
            return error_response("只支持wav、mp3格式音频特效")

        upload_dir = EFFECT_PATH
        filename = f"{str(uuid.uuid4())}.{file.name.split('.')[-1]}"
        file_path = os.path.join(upload_dir, filename)

        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
            # 获取音频时长
        try:
            audio = AudioSegment.from_file(file_path)
            duration = len(audio) / 1000.0  # 将毫秒转换为秒
        except Exception as e:
            return error_response(f"无法解析音频文件: {str(e)}")
        spec = {
            'duration': duration
        }
        Effects(name=name, effect_path=filename, desc=desc, spec=spec).save()

        return ok_response("ok")
