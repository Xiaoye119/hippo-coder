# coding=utf-8
"""
@Author: Jacob Y
@Date  : 12/20/2024
@Desc  : 
"""
import os

class VerilogFileProcessor:
    def __init__(self, project_path, output_file):
        """
        初始化 Verilog 文件处理器
        :param project_path: 项目的根目录
        :param output_file: 合并后输出的文件路径
        """
        self.project_path = project_path
        self.output_file = output_file
        self.supported_extensions = {".v", ".sv", ".vh", ".svh"}

    def find_verilog_files(self):
        """
        遍历项目目录，查找所有 Verilog 格式的文件
        :return: 包含文件路径的列表
        """
        verilog_files = []
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if os.path.splitext(file)[-1] in self.supported_extensions:
                    verilog_files.append(os.path.join(root, file))
        return verilog_files

    def merge_verilog_files(self, verilog_files):
        """
        将 Verilog 文件内容合并
        :param verilog_files: Verilog 文件路径列表
        """
        with open(self.output_file, 'w', encoding='utf-8') as outfile:
            for file in verilog_files:
                with open(file, 'r', encoding='utf-8') as infile:
                    # 添加文件分割标志
                    outfile.write(f"// Start of {file}\n")
                    outfile.write(infile.read())
                    outfile.write(f"\n// End of {file}\n\n")
        print(f"文件合并完成，结果已保存至 {self.output_file}")

    def run(self):
        """
        执行文件提取和合并操作
        """
        print(f"正在扫描路径: {self.project_path}")
        verilog_files = self.find_verilog_files()
        if not verilog_files:
            print("未找到 Verilog 文件")
            return

        print(f"找到 {len(verilog_files)} 个 Verilog 文件")
        self.merge_verilog_files(verilog_files)


# 使用示例
if __name__ == "__main__":
    # 设置项目路径和输出文件路径
    project_path = "testData/uhd-master"  # 替换为你的项目路径
    output_file = "merged_verilog.v"

    # 创建并运行 Verilog 文件处理器
    processor = VerilogFileProcessor(project_path, output_file)
    processor.run()
