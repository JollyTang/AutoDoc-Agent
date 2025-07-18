"""
AST解析器的单元测试

测试Python代码AST解析功能。
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.core.ast_parser import (
    PythonASTParser,
    parse_python_file,
    parse_python_source,
    parse_python_directory,
    ModuleInfo,
    FunctionInfo,
    ClassInfo
)
from src.core.language_detector import Language


class TestPythonASTParser:
    """Python AST解析器测试类"""
    
    def test_parse_simple_function(self):
        """测试解析简单函数"""
        source_code = '''
def hello_world():
    """简单的问候函数"""
    print("Hello, World!")
'''
        
        parser = PythonASTParser()
        module_info = parser.parse_source(source_code)
        
        assert module_info is not None
        assert module_info.name == "<string>"
        assert len(module_info.functions) == 1
        
        func = module_info.functions[0]
        assert func.name == "hello_world"
        assert func.docstring == "简单的问候函数"
        assert func.parameters == []
        assert func.is_async is False
        assert func.is_method is False
    
    def test_parse_function_with_parameters(self):
        """测试解析带参数的函数"""
        source_code = '''
def add(a: int, b: int) -> int:
    """加法函数"""
    return a + b
'''
        
        parser = PythonASTParser()
        module_info = parser.parse_source(source_code)
        
        assert module_info is not None
        assert len(module_info.functions) == 1
        
        func = module_info.functions[0]
        assert func.name == "add"
        assert func.docstring == "加法函数"
        assert func.parameters == ["a", "b"]
        assert func.return_type == "int"
    
    def test_parse_async_function(self):
        """测试解析异步函数"""
        source_code = '''
async def fetch_data(url: str) -> dict:
    """异步获取数据"""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
'''
        
        parser = PythonASTParser()
        module_info = parser.parse_source(source_code)
        
        assert module_info is not None
        assert len(module_info.functions) == 1
        
        func = module_info.functions[0]
        assert func.name == "fetch_data"
        assert func.docstring == "异步获取数据"
        assert func.parameters == ["url"]
        assert func.return_type == "dict"
        assert func.is_async is True
    
    def test_parse_class(self):
        """测试解析类"""
        source_code = '''
class Calculator:
    """计算器类"""
    
    def __init__(self, precision: int = 2):
        self.precision = precision
    
    def add(self, a: float, b: float) -> float:
        """加法运算"""
        return round(a + b, self.precision)
    
    @classmethod
    def create_default(cls) -> "Calculator":
        """创建默认计算器"""
        return cls()
'''
        
        parser = PythonASTParser()
        module_info = parser.parse_source(source_code)
        
        assert module_info is not None
        assert len(module_info.classes) == 1
        
        cls = module_info.classes[0]
        assert cls.name == "Calculator"
        assert cls.docstring == "计算器类"
        assert len(cls.methods) == 3
        
        # 检查__init__方法
        init_method = next(m for m in cls.methods if m.name == "__init__")
        assert init_method.parameters == ["self", "precision"]
        assert init_method.return_type == "None"
        assert init_method.is_method is True
        
        # 检查add方法
        add_method = next(m for m in cls.methods if m.name == "add")
        assert add_method.parameters == ["self", "a", "b"]
        assert add_method.return_type == "float"
        assert add_method.docstring == "加法运算"
        
        # 检查类方法
        create_method = next(m for m in cls.methods if m.name == "create_default")
        assert create_method.is_classmethod is True
        assert create_method.return_type == "Calculator"
    
    def test_parse_imports(self):
        """测试解析导入语句"""
        source_code = '''
import os
import sys
from typing import List, Dict, Optional
from pathlib import Path
from .utils import helper_function
'''
        
        parser = PythonASTParser()
        module_info = parser.parse_source(source_code)
        
        assert module_info is not None
        assert "os" in module_info.imports
        assert "sys" in module_info.imports
        assert "typing.List" in module_info.from_imports
        assert "typing.Dict" in module_info.from_imports
        assert "typing.Optional" in module_info.from_imports
        assert "pathlib.Path" in module_info.from_imports
        assert "utils.helper_function" in module_info.from_imports
    
    def test_parse_variables_and_constants(self):
        """测试解析变量和常量"""
        source_code = '''
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30
API_BASE_URL = "https://api.example.com"

user_name = "admin"
config = {"debug": True}
'''
        
        parser = PythonASTParser()
        module_info = parser.parse_source(source_code)
        
        assert module_info is not None
        assert "MAX_RETRIES" in module_info.constants
        assert "DEFAULT_TIMEOUT" in module_info.constants
        assert "API_BASE_URL" in module_info.constants
        assert "user_name" in module_info.variables
        assert "config" in module_info.variables
    
    def test_parse_module_docstring(self):
        """测试解析模块文档字符串"""
        source_code = '''
"""
这是一个示例模块

提供各种实用功能。
"""

def helper_function():
    pass
'''
        
        parser = PythonASTParser()
        module_info = parser.parse_source(source_code)
        
        assert module_info is not None
        assert module_info.docstring == "这是一个示例模块\n\n提供各种实用功能。"
    
    def test_parse_decorators(self):
        """测试解析装饰器"""
        source_code = '''
from functools import wraps

def my_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@my_decorator
@staticmethod
def decorated_function():
    pass
'''
        
        parser = PythonASTParser()
        module_info = parser.parse_source(source_code)
        
        assert module_info is not None
        assert len(module_info.functions) == 2
        
        # 检查装饰器函数
        decorator_func = next(f for f in module_info.functions if f.name == "my_decorator")
        assert len(decorator_func.decorators) == 0
        
        # 检查被装饰的函数
        decorated_func = next(f for f in module_info.functions if f.name == "decorated_function")
        assert "my_decorator" in decorated_func.decorators
        assert "staticmethod" in decorated_func.decorators
    
    def test_parse_file(self):
        """测试解析文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
def test_function():
    """测试函数"""
    return "test"
''')
            f.flush()
            
            try:
                parser = PythonASTParser()
                module_info = parser.parse_file(f.name)
                
                assert module_info is not None
                assert module_info.name == Path(f.name).stem
                assert module_info.file_path == f.name
                assert len(module_info.functions) == 1
                assert module_info.functions[0].name == "test_function"
            finally:
                os.unlink(f.name)
    
    def test_parse_non_python_file(self):
        """测试解析非Python文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is not Python code\n")
            f.flush()
            
            try:
                parser = PythonASTParser()
                module_info = parser.parse_file(f.name)
                
                assert module_info is None
            finally:
                os.unlink(f.name)
    
    def test_parse_directory(self):
        """测试解析目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建Python文件
            python_file = Path(temp_dir) / "test.py"
            python_file.write_text('''
def test_function():
    return "test"
''')
            
            # 创建非Python文件
            text_file = Path(temp_dir) / "test.txt"
            text_file.write_text("This is not Python")
            
            # 解析目录
            parser = PythonASTParser()
            results = parser.parse_directory(temp_dir)
            
            assert len(results) == 1
            assert str(python_file) in results
            assert results[str(python_file)].name == "test"
    
    def test_parse_directory_with_exclude(self):
        """测试带排除模式的目录解析"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建Python文件
            main_file = Path(temp_dir) / "main.py"
            main_file.write_text('''
def main():
    return "main"
''')
            
            # 创建应该被排除的文件
            excluded_file = Path(temp_dir) / "excluded.py"
            excluded_file.write_text('''
def excluded():
    return "excluded"
''')
            
            # 解析目录，排除特定文件
            parser = PythonASTParser()
            results = parser.parse_directory(temp_dir, exclude_patterns=["excluded"])
            
            assert len(results) == 1
            assert str(main_file) in results
            assert str(excluded_file) not in results


class TestASTParserFunctions:
    """AST解析器便捷函数测试类"""
    
    def test_parse_python_file_function(self):
        """测试parse_python_file便捷函数"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
def test():
    return "test"
''')
            f.flush()
            
            try:
                module_info = parse_python_file(f.name)
                assert module_info is not None
                assert module_info.name == Path(f.name).stem
            finally:
                os.unlink(f.name)
    
    def test_parse_python_source_function(self):
        """测试parse_python_source便捷函数"""
        source_code = '''
def test():
    return "test"
'''
        
        module_info = parse_python_source(source_code, "test_file.py")
        assert module_info is not None
        assert module_info.name == "test_file"
        assert len(module_info.functions) == 1
    
    def test_parse_python_directory_function(self):
        """测试parse_python_directory便捷函数"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建Python文件
            python_file = Path(temp_dir) / "test.py"
            python_file.write_text('''
def test():
    return "test"
''')
            
            # 解析目录
            results = parse_python_directory(temp_dir)
            
            assert len(results) == 1
            assert str(python_file) in results
            assert results[str(python_file)].name == "test"


class TestASTParserEdgeCases:
    """AST解析器边界情况测试类"""
    
    def test_parse_empty_file(self):
        """测试解析空文件"""
        parser = PythonASTParser()
        module_info = parser.parse_source("")
        
        assert module_info is not None
        assert module_info.name == "<string>"
        assert len(module_info.functions) == 0
        assert len(module_info.classes) == 0
    
    def test_parse_file_with_syntax_error(self):
        """测试解析语法错误的文件"""
        source_code = '''
def test_function(
    # 缺少闭合括号
'''
        
        parser = PythonASTParser()
        module_info = parser.parse_source(source_code)
        
        # 应该返回None或抛出异常
        assert module_info is None
    
    def test_parse_complex_nested_structure(self):
        """测试解析复杂的嵌套结构"""
        source_code = '''
class OuterClass:
    """外层类"""
    
    class InnerClass:
        """内层类"""
        
        def inner_method(self):
            """内层方法"""
            def nested_function():
                """嵌套函数"""
                return "nested"
            return nested_function()
    
    def outer_method(self):
        """外层方法"""
        return "outer"
'''
        
        parser = PythonASTParser()
        module_info = parser.parse_source(source_code)
        
        assert module_info is not None
        assert len(module_info.classes) == 1
        
        outer_class = module_info.classes[0]
        assert outer_class.name == "OuterClass"
        assert len(outer_class.methods) == 1  # 只有outer_method
        
        # 注意：内层类不会被解析为独立的方法，而是作为类体的一部分 