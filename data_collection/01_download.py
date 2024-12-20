# coding=utf-8
"""
@Author: Jacob Y
@Date  : 12/19/2024
@Desc  : 
"""
import re
import time
import requests
import os
import json
import traceback

proxy = {
    "http": "http://127.0.0.1:10792",
    "https": "http://127.0.0.1:10792",
}

# 读取JSON文件
def read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# 下载文件
def download_file(url, local_filename, proxies=None):
    try:
        response = requests.get(url, proxies=proxies, stream=True, timeout=10)
        response.raise_for_status()

        # 保存文件
        with open(local_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Downloaded: {local_filename}")
        return True
    except Exception as e:
        print(f"!!Failed to download {url}: {e}")
        return False

# 主函数
def main():
    json_file = "test/result_12_20_14_42.json"
    save_dir = 'zipfiles'

    # 创建保存目录
    os.makedirs(save_dir, exist_ok=True)

    data = read_json(json_file)
    failed_downloads = []

    # 下载每个链接
    for item in data:
        url = item.get('src')
        if not url:
            continue

        # 生成文件名
        title = re.findall(r'https://github.com/(.*?)/archive/refs/heads/master.zip', url)
        if title:
            title = title[0].replace("/", "_")
        else:
            title = "unk"
        local_filename = os.path.join(save_dir, f"{title}.zip")

        # 检查文件是否已存在
        if os.path.exists(local_filename):
            print(f"File already exists: {local_filename}. Skipping download.")
            continue

        # 下载文件
        if not download_file(url, local_filename, proxies=proxy):
            failed_downloads.append(url)

        time.sleep(1)
    # 记录失败的下载
    if failed_downloads:
        failed_log = os.path.join(save_dir, 'failed_downloads.json')
        with open(failed_log, 'w', encoding='utf-8') as file:
            json.dump(failed_downloads, file, ensure_ascii=False, indent=4)
        print(f"Failed downloads logged to {failed_log}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Unhandled exception occurred: {e}")
        traceback.print_exc()
