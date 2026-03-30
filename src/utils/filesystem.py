"""
文件系统工具模块

提供安全的文件读写操作
"""

from pathlib import Path
from typing import Union


class FileSystem:
    """文件系统操作工具"""
    
    def __init__(self, root_path: Union[str, Path]):
        """
        初始化文件系统工具
        
        Args:
            root_path: 根目录路径
        """
        self.root_path = Path(root_path).expanduser().resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)
    
    def read_file(self, file_path: str) -> str:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件内容
        """
        full_path = self._resolve_path(file_path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def write_file(self, file_path: str, content: str, 
                   overwrite: bool = False) -> None:
        """
        写入文件内容
        
        Args:
            file_path: 文件路径
            content: 文件内容
            overwrite: 是否覆盖现有文件
        """
        full_path = self._resolve_path(file_path)
        
        # 检查文件是否存在
        if full_path.exists() and not overwrite:
            raise FileExistsError(f"文件已存在: {file_path}")
        
        # 原子写入 (先写入临时文件，然后重命名)
        temp_path = full_path.with_suffix('.tmp')
        try:
            # 创建父目录
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入临时文件
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 重命名临时文件
            temp_path.rename(full_path)
        except Exception as e:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            raise e
    
    def delete_file(self, file_path: str) -> None:
        """
        删除文件 (移动到 .trash/)
        
        Args:
            file_path: 文件路径
        """
        full_path = self._resolve_path(file_path)
        trash_path = self.root_path / ".trash" / file_path
        
        # 创建回收站目录
        trash_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 移动到回收站
        full_path.rename(trash_path)
    
    def move_file(self, source_path: str, dest_path: str) -> None:
        """
        移动文件
        
        Args:
            source_path: 源路径
            dest_path: 目标路径
        """
        src_full = self._resolve_path(source_path)
        dest_full = self._resolve_path(dest_path)
        
        # 创建目标目录
        dest_full.parent.mkdir(parents=True, exist_ok=True)
        
        # 移动文件
        src_full.rename(dest_full)
    
    def list_files(self, directory: str = ".", 
                   recursive: bool = False) -> list:
        """
        列出目录中的文件
        
        Args:
            directory: 目录路径
            recursive: 是否递归
            
        Returns:
            list: 文件列表
        """
        dir_path = self._resolve_path(directory)
        
        if recursive:
            files = list(dir_path.rglob("*"))
        else:
            files = list(dir_path.glob("*"))
        
        # 过滤出文件
        files = [f for f in files if f.is_file()]
        
        # 转换为相对路径
        return [str(f.relative_to(self.root_path)) for f in files]
    
    def file_exists(self, file_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否存在
        """
        full_path = self._resolve_path(file_path)
        return full_path.exists()
    
    def _resolve_path(self, file_path: str) -> Path:
        """
        解析文件路径 (防止路径遍历攻击)
        
        Args:
            file_path: 文件路径
            
        Returns:
            Path: 解析后的路径
        """
        # 转换为 Path 对象
        path = Path(file_path)
        
        # 如果是绝对路径，使用根目录
        if path.is_absolute():
            path = path.relative_to(path.root)
        
        # 解析完整路径
        full_path = (self.root_path / path).resolve()
        
        # 检查是否在根目录内
        if not str(full_path).startswith(str(self.root_path)):
            raise ValueError(f"非法路径: {file_path}")
        
        return full_path


# 测试
if __name__ == "__main__":
    # 创建测试文件系统
    fs = FileSystem("/tmp/test-vault")
    
    # 创建测试文件
    test_file = "test.md"
    test_content = "# 测试文档\n\n这是测试内容"
    
    # 写入测试文件
    fs.write_file(test_file, test_content, overwrite=True)
    print(f"✅ 文件写入成功: {test_file}")
    
    # 读取测试文件
    content = fs.read_file(test_file)
    print(f"✅ 文件读取成功: {content}")
    
    # 列出文件
    files = fs.list_files()
    print(f"📁 目录文件: {files}")
    
    print("✅ 文件系统工具测试通过")