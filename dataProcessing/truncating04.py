# coding=utf-8
"""
@Author: Jacob Y
@Date  : 12/28/2024
@Desc  : 
"""
import os
import random


# 计算块大小
def calculate_block_size(remaining_lines):
    # 确保块大小在 11-60 行之间
    # 如果剩余行数少于10行，不切分，返回剩余行数
    if remaining_lines <= 10:
        return remaining_lines

    # 50%的块在 11-24 行之间
    if random.random() <= 0.5:
        block_size = random.randint(11, 24)
    # 25%的块在 25-45 行之间
    elif random.random() <= 0.25:
        block_size = random.randint(25, 45)
    # 25%的块在 46-60 行之间
    else:
        block_size = random.randint(46, 60)

    # 确保块大小不大于剩余行数
    return min(block_size, remaining_lines)


# 保存文件块
def save_block(lines, output_dir, filename, suffix):
    cleaned_lines = [line.rstrip('\n') for line in lines]
    block_content = "\n".join(cleaned_lines)

    block_filename = os.path.splitext(filename)[0] + suffix + ".v"
    block_filepath = os.path.join(output_dir, block_filename)

    with open(block_filepath, 'w', encoding="utf-8") as block_file:
        block_file.write(block_content)


# 处理Verilog文件
def process_verilog_file(input_file, output_dir):
    with open(input_file, 'r') as f:
        lines = f.readlines()

    total_lines = len(lines)
    current_line = 0
    file_suffix = 1

    while current_line < total_lines:
        # 计算剩余行数
        remaining_lines = total_lines - current_line

        # 计算当前块的大小
        block_size = calculate_block_size(remaining_lines)

        # 如果当前剩余行数少于10行，跳过切分直接合并
        if block_size <= 10:
            break

        # 获取当前块的行
        block_lines = lines[current_line:current_line + block_size]

        print(len(block_lines))
        # 保存当前块
        save_block(block_lines, output_dir, os.path.basename(input_file), f"_{file_suffix}")
        file_suffix += 1

        # 更新当前行
        current_line += block_size


# 主程序
def process_verilog_files(input_directory, output_directory, sample=None):
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    files = os.listdir(input_directory)[:sample] if sample else os.listdir(input_directory)
    for filename in files:
        input_file = os.path.join(input_directory, filename)
        if os.path.isfile(input_file) and filename.endswith(".v"):
            process_verilog_file(input_file, output_directory)


# 调用主函数
input_directory = "../data/code-verilog"  # 输入Verilog文件目录
output_directory = "./output"  # 输出子块文件目录

process_verilog_files(input_directory, output_directory, sample=1000)
