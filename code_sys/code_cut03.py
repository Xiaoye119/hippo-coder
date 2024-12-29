import os
import json
import glob
import random
import shutil  # 用于删除文件夹
from random import shuffle
from tqdm import tqdm  # 导入 tqdm 进度条

# 删除并重新创建输出文件夹
def reset_output_folders():
    if os.path.exists('output'):
        shutil.rmtree('output')  # 删除整个 output 文件夹
    os.makedirs('output')  # 重新创建 output 文件夹
    os.makedirs('output/task1')  # 创建 task1 子文件夹
    os.makedirs('output/task2')  # 创建 task2 子文件夹


# 按指定的概率和行数切割单个文件内容
def split_file_by_random_ratio(file_lines, line_ratios=None):
    if line_ratios is None:
        line_ratios = [
            (0.1, 10), (0.1, 20), (0.1, 30),
            (0.2, 40), (0.1, 50), (0.2, 60),
            (0.1, 80), (0.1, 100)
        ]

    # 随机选择一个比例
    ratio, end_line = random.choice(line_ratios)

    # 确保文件行数足够切割，否则整个文件作为一个块
    if len(file_lines) == 0:
        return []

    # 随机打乱代码行顺序
    shuffle(file_lines)

    # 获取切割的代码块数量
    chunk_size = max(1, int(len(file_lines) * ratio))  # 确保 chunk_size 至少为1

    chunks = []
    block_id = 1

    for i in range(0, len(file_lines), chunk_size):
        chunk = ''.join(file_lines[i:i + chunk_size]).strip()
        if chunk:  # 确保非空块才添加
            chunks.append({"language": "verilog", "code": chunk, "block_id": block_id})
            block_id += 1

    # 如果没有产生任何块，则将所有行作为单个块返回
    if not chunks and file_lines:
        chunk = ''.join(file_lines).strip()
        if chunk:
            chunks.append({"language": "verilog", "code": chunk, "block_id": 1})

    return chunks


# 掩码代码块
def mask_code_blocks(data):
    modes = ['mode1', 'mode2', 'mode3', 'mode4', 'mode5']
    output_data = []

    for entry in data:
        mode = random.choice(modes)

        prefix, middle, suffix = "", entry["code"], ""

        if mode == 'mode1':  # 单个单词 (符号)
            words = middle.split()
            if words:
                index = random.randint(0, len(words) - 1)
                prefix = ' '.join(words[:index])
                middle = words[index]
                suffix = ' '.join(words[index + 1:])
        elif mode == 'mode2':  # 多个单词
            words = middle.split()
            if len(words) > 1:
                start = random.randint(0, len(words) - 2)
                end = random.randint(start + 1, len(words))
                prefix = ' '.join(words[:start])
                middle = ' '.join(words[start:end])
                suffix = ' '.join(words[end:])
            else:
                prefix = middle
                suffix = ''
        elif mode == 'mode3':  # 整行
            lines = middle.split('\n')
            if len(lines) > 1:
                index = random.randint(0, len(lines) - 1)
                prefix = '\n'.join(lines[:index])
                middle = lines[index]
                suffix = '\n'.join(lines[index + 1:])
            else:
                prefix = middle
                suffix = ''
        elif mode == 'mode4':  # 多行
            lines = middle.split('\n')
            if len(lines) > 1:
                start = random.randint(0, len(lines) - 2)
                end = random.randint(start + 1, len(lines))
                prefix = '\n'.join(lines[:start])
                middle = '\n'.join(lines[start:end])
                suffix = '\n'.join(lines[end:])
            else:
                prefix = middle
                suffix = ''
        elif mode == 'mode5':  # 代码块
            lines = middle.split('\n')
            if len(lines) > 1:
                start = random.randint(0, len(lines) - 2)
                end = random.randint(start + 1, len(lines))
                prefix = '\n'.join(lines[:start])
                middle = '\n'.join(lines[start:end])
                suffix = '\n'.join(lines[end:])
            else:
                prefix = middle
                suffix = ''

        output_data.append({"language": "verilog", "prefix": prefix, "middle": middle, "suffix": suffix,
                            "block_id": entry["block_id"]})

    return output_data


# 主函数
def main():
    input_folder = 'code-verilog'  # 输入文件夹

    # 删除并重置输出文件夹
    reset_output_folders()

    result1_all_data = []
    result2_all_data = []

    # 获取所有 .v 文件的列表
    files_to_process = glob.glob(os.path.join(input_folder, '*.v'))

    # 使用一个总的 tqdm 来跟踪所有文件的处理进度
    with tqdm(total=len(files_to_process), desc="总进度", unit="文件") as pbar:
        for file in files_to_process:
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
                    pbar.update(1)  # 更新进度条，即使文件未成功处理
                    continue

            # 对每个文件按随机比例切割
            result1_data = split_file_by_random_ratio(all_lines)
            result1_all_data.extend(result1_data)

            # 对切割后的数据进行掩码操作
            result2_data = mask_code_blocks(result1_data)
            result2_all_data.extend(result2_data)

            pbar.update(1)  # 每处理完一个文件更新一次进度条

    # 写入 task1 的结果，每个块一行
    with open('output/task1/result1.jsonl', 'w', encoding='utf-8') as out_file:
        for entry in result1_all_data:
            out_file.write(json.dumps(entry, ensure_ascii=False) + '\n')

    # 写入 task2 的结果，每个块一行
    with open('output/task2/result2.jsonl', 'w', encoding='utf-8') as out_file:
        for entry in result2_all_data:
            out_file.write(json.dumps(entry, ensure_ascii=False) + '\n')

    # 所有操作完成后打印消息
    print("已完成本次数据处理！")


if __name__ == '__main__':
    main()