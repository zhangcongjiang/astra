import os

import paramiko
from PIL import Image

from astra.settings import IMG_PATH
from common.image_utils import ImageUtils

img_utils = ImageUtils()


def download(src_file):
    hostname = '39.98.165.125'
    port = 22
    username = 'root'
    password = 'Aliyun@19920926'

    # 创建SSH客户端
    client = paramiko.SSHClient()

    # 默认情况下，paramiko不会信任未知的主机，你需要手动添加主机密钥
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # 连接到服务器
    client.connect(hostname, port=port, username=username, password=password)

    # 使用SFTP下载文件
    sftp = client.open_sftp()
    local_file = os.path.join(IMG_PATH, src_file.split('/')[-1])
    sftp.get(src_file, local_file)

    # 关闭SFTP会话和SSH连接
    sftp.close()
    client.close()
    img = Image.open(local_file)
    img_resized = img_utils.resize_and_crop(img)
    img_resized.save(local_file)

    print("文件下载完成")
