# coding=utf-8
"""
@Author: Jacob Y
@Date  : 12/21/2024
@Desc  : 去除注释
"""
import re

def remove_comments_and_extract_verilog(file_content):
    """
    去除注释并提取 Verilog 代码。
    :param file_content: 文件内容（字符串形式）
    :return: 提取的 Verilog 代码（字符串）
    """
    # 去除单行注释
    no_single_line_comments = re.sub(r"//.*", "", file_content)

    # 去除多行注释
    no_comments = re.sub(r"/\\*.*?\\*/", "", no_single_line_comments, flags=re.DOTALL)

    # 使用正则提取 Verilog 模块
    verilog_code_blocks = re.findall(r"module.*?endmodule", no_comments, flags=re.DOTALL)

    # 拼接所有模块，返回干净的 Verilog 代码
    return "\n\n".join(verilog_code_blocks)

def process_verilog_file(input_file, output_file):
    """
    读取文件，提取 Verilog 代码并保存到新文件。
    :param input_file: 输入文件路径
    :param output_file: 输出文件路径
    """
    with open(input_file, 'r', encoding='utf-8') as infile:
        file_content = infile.read()

    verilog_code = remove_comments_and_extract_verilog(file_content)

    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write(verilog_code)

    print(f"提取完成，Verilog 代码已保存到 {output_file}")

# 示例调用
if __name__ == "__main__":
    input_path = "test.v"  # 替换为你的 Verilog 文件路径
    output_path = "cleaned_test.v"  # 替换为输出路径
    process_verilog_file(input_path, output_path)
