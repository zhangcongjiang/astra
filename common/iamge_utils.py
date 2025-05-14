from transparent_background import Remover
from PIL import Image


def transparent_img(img_path):
    remover = Remover()  # 默认模型配置
    img = Image.open(img_path).convert('RGB')
    return remover.process(img)
