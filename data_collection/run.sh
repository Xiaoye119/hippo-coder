#!/bin/bash

# 检查是否提供了目标路径和目标文件夹
if [ "$#" -ne 2 ]; then
    echo "使用方法: $0 <源路径> <目标文件夹>"
    exit 1
fi

# 获取目标路径和目标文件夹
TARGET_PATH=$1
DESTINATION_FOLDER=$2

# 检查目标路径是否存在
if [ ! -d "$TARGET_PATH" ]; then
    echo "源路径 $TARGET_PATH 不存在"
    exit 1
fi

# 检查目标文件夹是否存在，如果不存在则创建
if [ ! -d "$DESTINATION_FOLDER" ]; then
    echo "目标文件夹 $DESTINATION_FOLDER 不存在，正在创建..."
    mkdir -p "$DESTINATION_FOLDER"
fi

# 遍历目标路径下的所有ZIP文件并解压缩到目标文件夹
for zip_file in "$TARGET_PATH"/*.zip; do
    if [ -f "$zip_file" ]; then
        echo "解压缩 $zip_file 到 $DESTINATION_FOLDER"
        # zip_file = ../zipfiles/dragonlord1129_RISC-V-Simplified-Implementation.zip
        dir_name=$(basename "$zip_file" .zip)
        mkdir -p "$DESTINATION_FOLDER/$dir_name"
        unzip "$zip_file" -d "$DESTINATION_FOLDER/$dir_name"
    fi
done

echo "所有ZIP文件已解压缩到 $DESTINATION_FOLDER"