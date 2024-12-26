import os
import subprocess
import re
from tqdm import tqdm
import chardet
import pandas as pd


def check_iverilog_installed():
    """
    检查是否已安装 iverilog。

    Returns:
        bool: 如果已安装返回 True，否则 False。
    """
    try:
        subprocess.run(["iverilog", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        print("Error: iverilog 未安装或未配置在 PATH 中。\n"
              "请参考官方文档进行安装：https://iverilog.fandom.com/wiki/Installation")
        return False


def detect_encoding(file_path):
    """
    自动检测文件编码。

    Args:
        file_path (str): 文件路径。

    Returns:
        str: 文件编码格式。
    """
    with open(file_path, 'rb') as f:
        raw = f.read()
        result = chardet.detect(raw)
        return result['encoding']


def find_verilog_files(directory, recursive=False):
    """
    查找指定目录中的所有 .v 文件。

    Args:
        directory (str): 要查找的目录。
        recursive (bool): 是否递归查找子文件夹，默认为 False。

    Returns:
        list: 目录中的所有 .v 文件路径。
    """
    verilog_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".v"):
                verilog_files.append(os.path.join(root, file))
        if not recursive:
            break  # 不递归时只检查当前目录
    return verilog_files[:50]


def check_verilog_syntax(file_path, include_paths=None):
    """
    检查 Verilog 文件的语法错误，并计算错误行数占比。

    Args:
        file_path (str): Verilog 文件路径。
        include_paths (list, optional): 包含路径列表。

    Returns:
        dict: 包含是否成功、错误行数、总行数、错误比例的信息。
    """
    try:
        cmd = ["iverilog", "-t", "null"]
        if include_paths:
            for path in include_paths:
                cmd.extend(["-I", path])
        cmd.append(file_path)

        process = subprocess.run(
            cmd,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        # 如果没有异常被抛出，说明编译成功
        encoding = detect_encoding(file_path) or 'utf-8'
        with open(file_path, "r", encoding=encoding) as file:
            total_lines = sum(1 for _ in file)

        return {
            "file": file_path,
            "success": True,
            "total_lines": total_lines,
            "error_lines": 0,
            "error_ratio": 0,
            "errors": ""
        }
    except subprocess.CalledProcessError as e:
        error_lines = set()
        for line in e.stderr.splitlines():
            match = re.search(r"(\d+): error:", line)
            if match:
                error_lines.add(int(match.group(1)))

        encoding = detect_encoding(file_path) or 'utf-8'
        with open(file_path, "r", encoding=encoding) as file:
            total_lines = sum(1 for _ in file)

        error_count = len(error_lines)
        error_ratio = error_count / total_lines if total_lines > 0 else 0

        return {
            "file": file_path,
            "success": False,
            "total_lines": total_lines,
            "error_lines": error_count,
            "error_ratio": error_ratio,
            "errors": e.stderr.strip()  # 添加错误信息
        }
    except Exception as e:
        return {
            "file": file_path,
            "success": False,
            "total_lines": 0,
            "error_lines": 0,
            "error_ratio": 0,
            "errors": str(e)
        }


if __name__ == "__main__":
    if not check_iverilog_installed():
        exit(1)

    target_directory = os.getcwd()  # 使用当前工作目录
    recursive_search = True  # 可根据需要设置为 False
    include_paths = [os.getcwd()]  # 默认使用当前工作目录作为包含路径

    verilog_files = find_verilog_files(target_directory, recursive=recursive_search)
    total_files = len(verilog_files)
    successful_files = 0
    failed_files = 0

    results = []
    if not verilog_files:
        print(f"目录 '{target_directory}' 未找到任何 .v 文件。")
    else:
        print(f"在目录 '{target_directory}' 中找到以下 Verilog 文件：")
        for file in verilog_files:
            print(f"  - {os.path.relpath(file, target_directory)}")

        print("\n开始语法检查...")
        for file in tqdm(verilog_files, desc="检查进度"):
            result = check_verilog_syntax(file, include_paths)
            results.append(result)
            if result["success"]:
                successful_files += 1
            else:
                failed_files += 1

        print("\n检查结果汇总：")
        for result in results:
            print(f"\n文件: {os.path.relpath(result['file'], target_directory)}")
            if result["success"]:
                print("  语法检查成功")
            else:
                print("  语法检查失败")
                print(f"  总行数: {result['total_lines']}")
                print(f"  语法错误行数: {result['error_lines']}")
                print(f"  错误比例: {result['error_ratio']:.2%}")
                print(f"  错误详情:\n{result['errors']}")

        # 输出统计数据
        print("\n统计信息：")
        print(f"总共处理文件数量: {total_files}")
        print(f"成功运行的文件数量: {successful_files}")
        print(f"运行失败的文件数量: {failed_files}")

        # 准备数据以保存到Excel文件
        df_results = pd.DataFrame(results)
        df_results['能否运行'] = df_results['success'].apply(lambda x: '能' if x else '不能')
        df_results['文件名'] = df_results['file'].apply(lambda x: os.path.basename(x))
        df_results['语法情况记录'] = df_results.apply(
            lambda
                row: f"总行数: {row['total_lines']}, 语法错误行数: {row['error_lines']}, 错误比例: {row['error_ratio']:.2%}",
            axis=1)

        # 添加总体值
        summary = pd.DataFrame({
            '文件名': ['总计'],
            '能否运行': [f'{successful_files}/{total_files}'],
            '语法情况记录': [f"成功: {successful_files}, 失败: {failed_files}"]
        })

        # 将DataFrame保存为Excel文件
        with pd.ExcelWriter('verilog_syntax_check_results.xlsx', engine='openpyxl') as writer:
            df_results[['文件名', '能否运行', '语法情况记录']].to_excel(writer, sheet_name='Details', index=False)
            summary.to_excel(writer, sheet_name='Summary', index=False)

        print("\n所有结果已保存至 'verilog_syntax_check_results.xlsx'")
