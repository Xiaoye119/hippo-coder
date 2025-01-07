import os
import json
import glob
import random
import numpy as np
from tqdm import tqdm  # 导入 tqdm 进度条
import shutil  # 添加此行以导入 shutil 模块


# 删除并重新创建输出文件夹
def reset_output_folders():
    if os.path.exists(r'F:\hippo项目-bak\data\code-verilog\sft_cut'):
        shutil.rmtree(r'F:\hippo项目-bak\data\code-verilog\sft_cut')  # 删除整个文件夹
    os.makedirs(r'F:\hippo项目-bak\data\code-verilog\sft_cut')  # 重新创建文件夹
    os.makedirs(r'F:\hippo项目-bak\data\code-verilog\sft_cut\out_put\task1')  # 创建 task1 子文件夹
    os.makedirs(r'F:\hippo项目-bak\data\code-verilog\sft_cut\out_put\task2')  # 创建 task2 子文件夹
    os.makedirs(r'F:\hippo项目-bak\data\code-verilog\sft_cut\out_put\task3')  # 创建 task3 子文件夹


# 按概率切文件
def split_file_by_random_ratio(file_lines, file_name, file_index, line_ratios=None):
    if line_ratios is None:
        line_ratios = [
            (0.1, (1, 10)),
            (0.1, (11, 20)),
            (0.1, (21, 30)),
            (0.2, (31, 40)),
            (0.1, (41, 50)),
            (0.2, (51, 60)),
            (0.1, (61, 80)),
            (0.1, (81, 100))
        ]

    # 确保文件行数足够切割，否则整个文件作为一个块
    if len(file_lines) <= 5:  # 舍弃少于等于5行的文件
        return []

    chunks = []
    block_id = 1
    remaining_lines = list(file_lines)  # 使用列表副本以避免修改原始数据

    while remaining_lines:
        chosen_ratio, (min_lines, max_lines) = random.choice(line_ratios)

        # 如果剩余行数小于最小行数，则将剩余部分作为最后一个块
        if len(remaining_lines) < min_lines:
            chunk_size = len(remaining_lines)
        else:
            actual_max_lines = min(max_lines, len(remaining_lines))
            effective_min_lines = max(min_lines, 1)

            # 确保 chunk_size 在有效范围内，并且不超过最大行数限制
            chunk_size = min(random.randint(effective_min_lines, actual_max_lines), 100)

        chunk = ''.join(remaining_lines[:chunk_size]).strip()
        if chunk:
            chunks.append({
                "language": "verilog",
                "code": chunk,
                "block_id": f"block_id_{file_index}_{block_id}",
                "file_name": file_name  # 记录文件名
            })
            block_id += 1

        remaining_lines = remaining_lines[chunk_size:]

    return chunks


# 掩码策略
def mask_code_blocks(data, file_name, file_index):
    modes = ['mode1', 'mode2', 'mode3', 'mode4', 'mode5']
    output_data = []

    for entry in data:
        mode = random.choice(modes)
        code = entry["code"]

        prefix, middle, suffix = "", code, ""

        if mode == 'mode1':  # 单个单词 (符号)
            words = code.split()
            if words:
                index = random.randint(0, len(words) - 1)
                prefix = ' '.join(words[:index])
                middle = words[index]
                suffix = ' '.join(words[index + 1:])
        elif mode == 'mode2':  # 多个单词
            words = code.split()
            if len(words) > 1:
                start = random.randint(0, len(words) - 2)
                end = random.randint(start + 1, len(words))
                prefix = ' '.join(words[:start])
                middle = ' '.join(words[start:end])
                suffix = ' '.join(words[end:])
            else:
                prefix = code
                suffix = ''
        elif mode == 'mode3':  # 整行
            lines = code.split('\n')
            if len(lines) > 1:
                index = random.randint(0, len(lines) - 1)
                prefix = '\n'.join(lines[:index])
                middle = lines[index]
                suffix = '\n'.join(lines[index + 1:])
            else:
                prefix = code
                suffix = ''
        elif mode == 'mode4':  # 多行
            lines = code.split('\n')
            if len(lines) > 1:
                # 随机选择 PSM 或 SPM 模式
                if random.random() < 0.5:  # PSM 模式
                    # PSM 模式：prefix、middle、suffix 都不能为 0
                    start = random.randint(1, len(lines) - 2)  # prefix 至少 1 行
                    end = random.randint(start + 1, len(lines) - 1)  # suffix 至少 1 行
                else:  # SPM 模式
                    # SPM 模式：prefix 必须为空，middle 和 suffix 不能为 0
                    start = 0  # prefix 必须为空
                    end = random.randint(1, len(lines) - 1)  # suffix 至少 1 行

                prefix = '\n'.join(lines[:start])
                middle = '\n'.join(lines[start:end])
                suffix = '\n'.join(lines[end:])
            else:
                prefix = code
                suffix = ''
        elif mode == 'mode5':  # 代码块
            lines = code.split('\n')
            if len(lines) > 1:
                # 随机选择 PSM 或 SPM 模式
                if random.random() < 0.5:  # PSM 模式
                    # PSM 模式：prefix、middle、suffix 都不能为 0
                    start = random.randint(1, len(lines) - 2)  # prefix 至少 1 行
                    end = random.randint(start + 1, len(lines) - 1)  # suffix 至少 1 行
                else:  # SPM 模式
                    # SPM 模式：prefix 必须为空，middle 和 suffix 不能为 0
                    start = 0  # prefix 必须为空
                    end = random.randint(1, len(lines) - 1)  # suffix 至少 1 行

                prefix = '\n'.join(lines[:start])
                middle = '\n'.join(lines[start:end])
                suffix = '\n'.join(lines[end:])
            else:
                prefix = code
                suffix = ''

        # 确保 PSM 模式下 prefix、middle、suffix 都不为 0
        if random.random() < 0.5:  # PSM 模式
            if not prefix or not middle or not suffix:
                continue  # 跳过不符合条件的块
        else:  # SPM 模式
            if not middle or not suffix:
                continue  # 跳过不符合条件的块

        output_data.append({
            "language": "verilog",
            "prefix": prefix,
            "middle": middle,
            "suffix": suffix,
            "block_id": entry["block_id"],
            "file_name": file_name
        })

    return output_data


# 关键词掩码策略
def mask_keywords(file_lines):
    """
    每读取 5 行代码，随机选择一个单词作为关键词，并将第一个字母作为 prefix，剩下的字母作为 middle。
    如果抽取的单词的第一个字符不是英文字母，则重新抽取。
    """
    keyword_data = []
    block_id = 1

    for i in range(0, len(file_lines), 5):
        # 获取 5 行代码
        chunk = file_lines[i:i + 5]
        words = [word for line in chunk for word in line.split() if word]  # 提取所有非空单词

        if not words:
            continue  # 如果没有单词，跳过

        # 随机选择一个单词，并确保第一个字符是英文字母
        max_attempts = 100  # 设定最大尝试次数，可以根据实际需求调整
        attempt_count = 0  # 初始化尝试次数计数器
        keyword_flag = True
        while True:
            keyword = random.choice(words)
            if len(keyword) > 0 and keyword[0].isalpha():  # 检查第一个字符是否为英文字母
                break
            attempt_count += 1
            if attempt_count >= max_attempts:
                keyword_flag = False
                print("已达到最大尝试次数，仍未找到符合条件的keyword，退出循环")
                break

        if not keyword_flag:
            continue

        if len(keyword) > 1:
            prefix = "<p>" + keyword[0]  # 第一个字母作为 prefix
            middle = "<m>" + keyword[1:]  # 剩下的字母作为 middle
        else:
            prefix = "<p>" + keyword
            middle = "<m>"

        keyword_data.append({
            "language": "verilog",
            "prefix": prefix,
            "middle": middle,
            "block_id": block_id
        })
        block_id += 1

    return keyword_data


# 主函数
def main():
    input_folder = r'F:\hippo项目-bak\data\code-verilog\code-verilog'  # 输入文件夹

    # 删除并重置输出文件夹
    reset_output_folders()

    result1_all_data = []
    result2_all_data = []
    result3_all_data = []  # 新增 task3 的结果数据列表

    # 获取所有 .v 文件的列表
    files_to_process = glob.glob(os.path.join(input_folder, '*.v'))

    # 记录无法处理的文件的日志
    error_log_file = 'error_files.log'
    with open(error_log_file, 'w', encoding='utf-8') as log_file:
        log_file.write("无法处理的文件列表：\n")

    # 设置最大处理文件数量
    max_files_to_process = 130000  # 控制处理 n 个文件
    processed_files_count = 0  # 已处理的文件数量计数器

    # 使用一个总的 tqdm 来跟踪所有文件的处理进度
    with tqdm(total=min(len(files_to_process), max_files_to_process), desc="总进度", unit="文件") as pbar:
        file_index = 1  # 文件计数器从1开始
        for file in files_to_process:
            if processed_files_count >= max_files_to_process:
                break  # 达到最大处理数量后停止
            try:
                all_lines = []
                try:
                    with open(file, 'r', encoding='utf-8', errors='replace') as f:
                        all_lines.extend(f.readlines())
                except UnicodeDecodeError:
                    print(f"无法用 utf-8 解码文件 {file}，尝试使用 gbk 编码...")
                    try:
                        with open(file, 'r', encoding='gbk', errors='replace') as f:
                            all_lines.extend(f.readlines())
                    except Exception as e:
                        print(f"读取文件 {file} 失败: {e}")
                        with open(error_log_file, 'a', encoding='utf-8') as log_file:
                            log_file.write(f"{file}\n")
                        pbar.update(1)  # 更新进度条，即使文件未成功处理
                        file_index += 1
                        processed_files_count += 1
                        continue

                # 对每个文件按随机比例切割
                file_name = os.path.basename(file)  # 获取文件名
                result1_data = split_file_by_random_ratio(all_lines, file_name, file_index)
                result1_all_data.extend(result1_data)

                # 对切割后的数据进行掩码操作
                result2_data = mask_code_blocks(result1_data, file_name, file_index)
                result2_all_data.extend(result2_data)

                # TODO 61460 在使用关键词掩码策略(这一行卡死的)
                result3_data = mask_keywords(all_lines)
                result3_all_data.extend(result3_data)

                pbar.update(1)  # 每处理完一个文件更新一次进度条
                file_index += 1  # 更新文件计数器
                processed_files_count += 1  # 更新已处理的文件数量
            except Exception as e:
                # 记录无法处理的文件的文件名
                # with open(error_log_file, 'a', encoding='utf-8') as log_file:
                #     log_file.write(f"{file}\n")
                # print(f"文件 {file} 处理失败: {e}")
                pbar.update(1)  # 更新进度条
                file_index += 1  # 更新文件计数器
                processed_files_count += 1  # 更新已处理的文件数量
                continue

    print("------------------------------------------------ 开始写入数据 -----------------------------------------------")
    # 写入 task1 的结果，每个块一行，并且每个块之间加个空行，同时格式化JSON对象
    with tqdm(total=len(result1_all_data), desc="写入 task1", unit="块") as pbar:
        with open(r'F:\hippo项目-bak\data\code-verilog\sft_cut\out_put\task1\result1.jsonl', 'w', encoding='utf-8') as out_file:
            for entry in result1_all_data:
                # 使用 indent 和 separators 参数使 JSON 输出更易读
                formatted_entry = json.dumps(entry, ensure_ascii=False, indent=4, separators=(',', ': '))
                out_file.write(formatted_entry + '\n\n')  # 每个块之间加个空行
                pbar.update(1)  # 更新进度条

    # 写入 task2 的结果，每个块一行，并且每个块之间加个空行，同时格式化JSON对象
    with tqdm(total=len(result2_all_data), desc="写入 task2", unit="块") as pbar:
        with open(r'F:\hippo项目-bak\data\code-verilog\sft_cut\out_put\task2\result2.jsonl', 'w', encoding='utf-8') as out_file:
            for entry in result2_all_data:
                # 使用 indent 和 separators 参数使 JSON 输出更易读
                formatted_entry = json.dumps(entry, ensure_ascii=False, indent=4, separators=(',', ': '))
                out_file.write(formatted_entry + '\n\n')  # 每个块之间加个空行
                pbar.update(1)  # 更新进度条

    # 写入 task3 的结果，每个块一行，并且每个块之间加个空行，同时格式化JSON对象
    with tqdm(total=len(result3_all_data), desc="写入 task3", unit="块") as pbar:
        with open(r'F:\hippo项目-bak\data\code-verilog\sft_cut\out_put\task3\result3.jsonl', 'w', encoding='utf-8') as out_file:
            for entry in result3_all_data:
                # 使用 indent 和 separators 参数使 JSON 输出更易读
                formatted_entry = json.dumps(entry, ensure_ascii=False, indent=4, separators=(',', ': '))
                out_file.write(formatted_entry + '\n\n')  # 每个块之间加个空行
                pbar.update(1)  # 更新进度条

    # 所有操作完成后打印消息
    print("已完成本次数据处理！")
    print(f"无法处理的文件已记录到 {error_log_file}")
    print(f"共处理了 {processed_files_count} 个文件")


if __name__ == '__main__':
    main()