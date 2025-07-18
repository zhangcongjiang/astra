from PIL import Image
from rembg import remove


class ImageUtils:
    @staticmethod
    def transparent_img(img_path):
        img = Image.open(img_path)
        return remove(img)
