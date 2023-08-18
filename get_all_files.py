import os 
def merge_text_and_code_files_in_current_directory():
    directory = '.'  # 默认当前目录
    output_filename = 'merged_content.txt'
    
    # 包括常见的文本文件和代码文件扩展名
    valid_extensions = [
        '.txt', '.md', '.csv', '.log', '.json', '.xml', '.html', '.htm', '.yaml', '.yml',
        '.py', '.js', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go', '.rb', '.php', 
        '.swift', '.sh', '.bat', '.r', '.m', '.f', '.f90', '.perl', '.pl', '.lua'
    ]
    
    # 检查目录是否存在
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return
    
    with open(output_filename, 'w', encoding='utf-8') as output_file:
        # 遍历文件夹中的所有文件
        for root, dirs, files in os.walk(directory):
            for file in files:
                # 判断文件扩展名是否属于文本或代码文件
                if any(file.lower().endswith(ext) for ext in valid_extensions):
                    # 获取完整文件路径
                    full_path = os.path.join(root, file)
                    # 将文件名写入目标txt文件作为注释
                    output_file.write(f"### {file} ###\n")
                    
                    # 使用缓冲方式读取和写入文件内容，以避免内存错误
                    with open(full_path, 'r', encoding='utf-8', errors='ignore') as input_file:
                        while True:
                            content = input_file.read(8192)  # 读取8KB的内容
                            if not content:
                                break
                            output_file.write(content)
                        output_file.write('\n\n')

# 运行函数
merge_text_and_code_files_in_current_directory()
