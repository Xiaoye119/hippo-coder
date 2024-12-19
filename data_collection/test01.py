# coding=utf-8
"""
@Author: Jacob Y
@Date  : 12/19/2024
@Desc  : 
"""
import requests
import os
from datetime import datetime


proxy = {
    "http": "http://127.0.0.1:10792",
    "https": "http://127.0.0.1:10792",
}


def download_file(url, local_filename=None):
    # 如果没有指定本地文件名，则根据URL的最后一部分创建一个默认文件名
    if not local_filename:
        local_filename = url.split('/')[-1]

    # 发送HTTP GET请求以获取文件内容
    response = requests.get(url, stream=True, proxies=proxy)

    # 检查请求是否成功
    if response.status_code == 200:
        # 打开一个文件以二进制写入模式保存文件
        with open(local_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"File downloaded successfully and saved as {local_filename}")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")


def main():
    url = "https://github.com/omarelhedaby/CNN-FPGA/archive/refs/heads/master.zip"

    # 可选：根据当前时间生成唯一的文件名
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    local_filename = f"CNN-FPGA_master_{timestamp}.zip"

    download_file(url, local_filename)


if __name__ == "__main__":
    main()

