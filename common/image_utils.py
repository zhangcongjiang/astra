import traceback

from PIL import Image
from rembg import remove


class ImageUtils:
    @staticmethod
    def transparent_img(img_path):
        img = Image.open(img_path)
        return remove(img)

    def resize_and_crop(self, img, target_width=1280, target_height=720):

        original_width, original_height = img.size

        # 计算新的尺寸
        aspect_ratio = target_width / target_height
        img_aspect_ratio = original_width / original_height

        if img_aspect_ratio > aspect_ratio:
            # 原图宽高比大于目标宽高比，意味着宽度超标，需要裁剪宽度
            new_height = target_height
            new_width = int(target_height * img_aspect_ratio)
        else:
            # 原图宽高比小于目标宽高比，意味着高度超标，需要裁剪高度
            new_width = target_width
            new_height = int(target_width / img_aspect_ratio)

        # 调整图像尺寸
        img = img.resize((new_width, new_height), Image.LANCZOS)

        # 计算裁剪位置
        left = (new_width - target_width) / 2
        top = 0  # 不裁剪顶部
        right = left + target_width
        bottom = target_height

        # 裁剪图像
        img = img.crop((int(left), int(top), int(right), int(bottom)))
        return img

    def trim_image(self, image_path, ):
        # 打开图片
        try:
            img = Image.open(image_path).convert("RGBA")
            # 获取图片的非透明部分的边界框
            bbox = img.getbbox()

            # 如果图片完全透明，则bbox会返回None
            if bbox is None:
                # 这种情况需要特别处理，或者返回错误
                print("Image is completely transparent!")
                return

                # 裁剪图片到非透明部分
            cropped_img = img.crop(bbox)

            return cropped_img
        except Exception:
            print(traceback.format_exc())