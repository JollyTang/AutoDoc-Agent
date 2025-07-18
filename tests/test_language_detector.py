"""
语言检测模块的单元测试

测试编程语言检测功能。
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.core.language_detector import (
    Language, 
    LanguageDetector, 
    detect_language, 
    detect_languages_in_directory,
    get_supported_languages
)


class TestLanguageDetector:
    """语言检测器测试类"""
    
    def test_detect_python_by_extension(self):
        """测试通过扩展名检测Python文件"""
        detector = LanguageDetector()
        
        # 创建临时文件进行测试
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('test')\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.PYTHON
            finally:
                os.unlink(f.name)
    
    def test_detect_go_by_extension(self):
        """测试通过扩展名检测Go文件"""
        detector = LanguageDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.go', delete=False) as f:
            f.write("package main\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.GO
            finally:
                os.unlink(f.name)
    
    def test_detect_java_by_extension(self):
        """测试通过扩展名检测Java文件"""
        detector = LanguageDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
            f.write("public class Main {}\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.JAVA
            finally:
                os.unlink(f.name)
    
    def test_detect_typescript_by_extension(self):
        """测试通过扩展名检测TypeScript文件"""
        detector = LanguageDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write("console.log('test');\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.TYPESCRIPT
            finally:
                os.unlink(f.name)
    
    def test_detect_javascript_by_extension(self):
        """测试通过扩展名检测JavaScript文件"""
        detector = LanguageDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write("console.log('test');\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.JAVASCRIPT
            finally:
                os.unlink(f.name)
    
    def test_detect_rust_by_extension(self):
        """测试通过扩展名检测Rust文件"""
        detector = LanguageDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rs', delete=False) as f:
            f.write("fn main() {}\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.RUST
            finally:
                os.unlink(f.name)
    
    def test_detect_cpp_by_extension(self):
        """测试通过扩展名检测C++文件"""
        detector = LanguageDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as f:
            f.write("#include <iostream>\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.CPP
            finally:
                os.unlink(f.name)
    
    def test_detect_c_by_extension(self):
        """测试通过扩展名检测C文件"""
        detector = LanguageDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write("#include <stdio.h>\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.C
            finally:
                os.unlink(f.name)
    
    def test_detect_config_files(self):
        """测试检测配置文件"""
        detector = LanguageDetector()
        
        # 测试Python配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False) as f:
            # 重命名文件为正确的配置文件名
            f.close()
            config_path = Path(f.name).parent / "requirements.txt"
            os.rename(f.name, config_path)
            
            try:
                with open(config_path, 'w') as f:
                    f.write("requests==2.31.0\n")
                
                assert detector.detect_language(str(config_path)) == Language.PYTHON
            finally:
                if config_path.exists():
                    os.unlink(config_path)
        
        # 测试Go配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False) as f:
            # 重命名文件为正确的配置文件名
            f.close()
            config_path = Path(f.name).parent / "go.mod"
            os.rename(f.name, config_path)
            
            try:
                with open(config_path, 'w') as f:
                    f.write("module test\n")
                
                assert detector.detect_language(str(config_path)) == Language.GO
            finally:
                if config_path.exists():
                    os.unlink(config_path)
    
    def test_detect_by_content_python(self):
        """测试通过内容检测Python文件"""
        detector = LanguageDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("def hello_world():\n    print('Hello, World!')\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.PYTHON
            finally:
                os.unlink(f.name)
    
    def test_detect_by_content_go(self):
        """测试通过内容检测Go文件"""
        detector = LanguageDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("package main\n\nfunc main() {\n    fmt.Println('Hello, World!')\n}\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.GO
            finally:
                os.unlink(f.name)
    
    def test_detect_by_content_java(self):
        """测试通过内容检测Java文件"""
        detector = LanguageDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("public class Main {\n    public static void main(String[] args) {\n        System.out.println('Hello, World!');\n    }\n}\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.JAVA
            finally:
                os.unlink(f.name)
    
    def test_detect_by_content_javascript(self):
        """测试通过内容检测JavaScript文件"""
        detector = LanguageDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("function helloWorld() {\n    console.log('Hello, World!');\n}\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.JAVASCRIPT
            finally:
                os.unlink(f.name)
    
    def test_detect_by_shebang(self):
        """测试通过shebang检测语言"""
        detector = LanguageDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("#!/usr/bin/env python3\nprint('Hello, World!')\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.PYTHON
            finally:
                os.unlink(f.name)
    
    def test_detect_unknown_file(self):
        """测试检测未知文件类型"""
        detector = LanguageDetector()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.unknown', delete=False) as f:
            f.write("This is some random content\n")
            f.flush()
            
            try:
                assert detector.detect_language(f.name) == Language.UNKNOWN
            finally:
                os.unlink(f.name)
    
    def test_file_not_found(self):
        """测试文件不存在的情况"""
        detector = LanguageDetector()
        
        with pytest.raises(FileNotFoundError):
            detector.detect_language("nonexistent_file.py")
    
    def test_get_supported_languages(self):
        """测试获取支持的语言列表"""
        detector = LanguageDetector()
        supported = detector.get_supported_languages()
        
        assert Language.PYTHON in supported
        assert Language.GO in supported
        assert Language.JAVA in supported
        assert Language.TYPESCRIPT in supported
        assert Language.JAVASCRIPT in supported
        assert Language.UNKNOWN not in supported
    
    def test_is_supported_language(self):
        """测试检查是否为支持的语言"""
        detector = LanguageDetector()
        
        assert detector.is_supported_language(Language.PYTHON) is True
        assert detector.is_supported_language(Language.GO) is True
        assert detector.is_supported_language(Language.UNKNOWN) is False


class TestLanguageDetectorFunctions:
    """语言检测器便捷函数测试类"""
    
    def test_detect_language_function(self):
        """测试detect_language便捷函数"""
        # 这个测试依赖于文件扩展名检测
        # 由于便捷函数内部调用detector.detect_language，我们测试一个简单的扩展名
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('test')\n")
            f.flush()
            
            try:
                assert detect_language(f.name) == Language.PYTHON
            finally:
                os.unlink(f.name)
    
    def test_get_supported_languages_function(self):
        """测试get_supported_languages便捷函数"""
        supported = get_supported_languages()
        
        assert Language.PYTHON in supported
        assert Language.GO in supported
        assert Language.JAVA in supported
        assert Language.UNKNOWN not in supported
    
    def test_detect_languages_in_directory(self):
        """测试目录语言检测"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            python_file = Path(temp_dir) / "test.py"
            python_file.write_text("print('test')\n")
            
            go_file = Path(temp_dir) / "main.go"
            go_file.write_text("package main\n\nfunc main() {}\n")
            
            # 检测目录中的语言
            result = detect_languages_in_directory(temp_dir)
            
            assert Language.PYTHON in result
            assert Language.GO in result
            assert str(python_file) in result[Language.PYTHON]
            assert str(go_file) in result[Language.GO]
    
    def test_detect_languages_in_directory_with_exclude(self):
        """测试带排除模式的目录语言检测"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            python_file = Path(temp_dir) / "test.py"
            python_file.write_text("print('test')\n")
            
            # 创建应该被排除的文件
            excluded_file = Path(temp_dir) / "excluded.py"
            excluded_file.write_text("print('excluded')\n")
            
            # 检测目录中的语言，排除特定文件
            result = detect_languages_in_directory(temp_dir, exclude_patterns=["excluded"])
            
            assert Language.PYTHON in result
            assert str(python_file) in result[Language.PYTHON]
            assert str(excluded_file) not in result[Language.PYTHON] 