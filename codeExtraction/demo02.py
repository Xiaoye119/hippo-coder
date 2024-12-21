# coding=utf-8
"""
@Author: Jacob Y
@Date  : 12/21/2024
@Desc  : 将{".v", ".sv", ".vh", ".svh", ".vp", ".vlog"}各自合并为单个文件
"""
import os

class VerilogFileProcessor:
    def __init__(self, project_path, output_dir):
        """
        初始化 Verilog 文件处理器
        :param project_path: 项目的根目录
        :param output_dir: 合并后输出的目录
        """
        self.project_path = project_path
        self.output_dir = output_dir
        self.supported_extensions = {".v", ".sv", ".vh", ".svh", ".vp", ".vlog"}

    def find_verilog_files(self):
        """
        遍历项目目录，查找所有 Verilog 格式的文件
        :return: 包含文件路径的字典，按扩展名分类
        """
        verilog_files = {ext: [] for ext in self.supported_extensions}
        for root, _, files in os.walk(self.project_path):
            for file in files:
                ext = os.path.splitext(file)[-1]
                if ext in self.supported_extensions:
                    verilog_files[ext].append(os.path.join(root, file))
        return verilog_files

    def merge_verilog_files(self, file_type, files):
        """
        将指定类型的 Verilog 文件内容合并
        :param file_type: 文件后缀类型
        :param files: Verilog 文件路径列表
        """
        output_file = os.path.join(self.output_dir, f"merged{file_type}")
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for file in files:
                with open(file, 'r', encoding='utf-8') as infile:
                    # 添加文件分割标志
                    outfile.write(f"// Start of {file}\n")
                    outfile.write(infile.read())
                    outfile.write(f"\n// End of {file}\n\n")
        print(f"文件合并完成: {output_file}")

    def run(self):
        """
        执行文件提取和合并操作
        """
        print(f"正在扫描路径: {self.project_path}")
        verilog_files = self.find_verilog_files()
        if not any(verilog_files.values()):
            print("未找到 Verilog 文件")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        for ext, files in verilog_files.items():
            if files:
                print(f"找到 {len(files)} 个 {ext} 文件")
                self.merge_verilog_files(ext, files)

# 使用示例
if __name__ == "__main__":
    project_path = "testData/"
    output_dir = "output"

    # 创建并运行 Verilog 文件处理器
    processor = VerilogFileProcessor(project_path, output_dir)
    processor.run()
