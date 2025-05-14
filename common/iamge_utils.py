from rembg import remove
from PIL import Image


class ImageUtils:
    @staticmethod
    def transparent_img(img_path):
        img = Image.open(img_path)
        return remove(img)
