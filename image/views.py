import mimetypes
import os
import uuid

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

from astra.settings import IMG_PATH
from common.response import error_response, ok_response
from image.models import Image


class ImageUploadView(generics.CreateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Upload an image",
        manual_parameters=[
            openapi.Parameter(
                'file', openapi.IN_FORM, description="Image file to upload", type=openapi.TYPE_FILE, required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Image uploaded successfully",
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
        if not file:
            return error_response("未提供图片")
        valid_mime_types = ['image/jpeg', 'image/png', 'image/jpg']
        mime_type, _ = mimetypes.guess_type(file.name)

        if mime_type not in valid_mime_types:
            return error_response("只支持jpeg、png、jpg格式图片")
        upload_dir = IMG_PATH
        filename = f"{str(uuid.uuid4())}.{file.name.split('.')[-1]}"
        file_path = os.path.join(upload_dir, filename)

        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        Image(img_name=filename).save()

        return ok_response("ok")
