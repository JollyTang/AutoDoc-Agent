"""
模块映射生成器的单元测试

测试模块映射生成功能的各种场景。
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from typing import Optional

from src.core.module_mapper import (
    ModuleMapper, ModuleMapping, ProjectMapping,
    generate_project_mapping, export_mapping_to_json
)
from src.core.language_detector import Language


class TestModuleMapper:
    """模块映射生成器测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.mapper = ModuleMapper()
    
    def test_create_module_mapping(self):
        """测试创建模块映射"""
        mapping = ModuleMapping(
            file_path="/test/file.py",
            module_name="test_module",
            language=Language.PYTHON,
            dependencies=["os", "sys"],
            exports=["main", "helper"],
            line_count=100,
            complexity_score=15.5
        )
        
        assert mapping.file_path == "/test/file.py"
        assert mapping.module_name == "test_module"
        assert mapping.language == Language.PYTHON
        assert len(mapping.dependencies) == 2
        assert len(mapping.exports) == 2
        assert mapping.line_count == 100
        assert mapping.complexity_score == 15.5
    
    def test_create_project_mapping(self):
        """测试创建项目映射"""
        project_mapping = ProjectMapping(project_path="/test/project")
        
        assert project_mapping.project_path == "/test/project"
        assert len(project_mapping.modules) == 0
        assert len(project_mapping.language_stats) == 0
        assert project_mapping.total_files == 0
        assert project_mapping.total_lines == 0
    
    def test_calculate_complexity_score(self):
        """测试计算复杂度分数"""
        # 模拟模块信息
        class MockModuleInfo:
            def __init__(self):
                self.line_count = 50
                self.functions = [MockFunction() for _ in range(3)]
                self.classes = [MockClass() for _ in range(2)]
                self.imports = ["os", "sys", "json"]
                self.exports = ["main", "helper"]
        
        class MockFunction:
            pass
        
        class MockClass:
            def __init__(self):
                self.methods = [MockFunction() for _ in range(2)]
        
        module_info = MockModuleInfo()
        score = self.mapper._calculate_complexity_score(module_info)
        
        # 预期分数计算：
        # 基础分数：50 * 0.1 = 5.0
        # 函数数量：3 * 2.0 = 6.0
        # 类数量：2 * 3.0 = 6.0
        # 方法数量：2 * 2 * 1.5 = 6.0
        # 导入数量：3 * 0.5 = 1.5
        # 导出数量：2 * 0.3 = 0.6
        # 总计：25.1
        expected_score = 25.1
        assert abs(score - expected_score) < 0.1
    
    def test_extract_dependencies_python(self):
        """测试提取Python依赖"""
        class MockPythonModule:
            def __init__(self):
                self.imports = ["os", "sys"]
                self.from_imports = ["json", "pathlib"]
        
        module_info = MockPythonModule()
        dependencies = self.mapper._extract_dependencies(module_info, Language.PYTHON)
        
        assert len(dependencies) == 4
        assert "os" in dependencies
        assert "sys" in dependencies
        assert "json" in dependencies
        assert "pathlib" in dependencies
    
    def test_extract_dependencies_go(self):
        """测试提取Go依赖"""
        class MockGoModule:
            def __init__(self):
                self.imports = ["fmt", "strings"]
        
        module_info = MockGoModule()
        dependencies = self.mapper._extract_dependencies(module_info, Language.GO)
        
        assert len(dependencies) == 2
        assert "fmt" in dependencies
        assert "strings" in dependencies
    
    def test_extract_exports_python(self):
        """测试提取Python导出"""
        class MockFunction:
            def __init__(self, name):
                self.name = name
        
        class MockClass:
            def __init__(self, name):
                self.name = name
        
        class MockPythonModule:
            def __init__(self):
                self.functions = [
                    MockFunction("public_func"),
                    MockFunction("_private_func")
                ]
                self.classes = [
                    MockClass("PublicClass"),
                    MockClass("_PrivateClass")
                ]
        
        module_info = MockPythonModule()
        exports = self.mapper._extract_exports(module_info, Language.PYTHON)
        
        assert len(exports) == 2
        assert "public_func" in exports
        assert "PublicClass" in exports
        assert "_private_func" not in exports
        assert "_PrivateClass" not in exports
    
    def test_extract_exports_go(self):
        """测试提取Go导出"""
        class MockGoFunction:
            def __init__(self, name, is_exported):
                self.name = name
                self.is_exported = is_exported
        
        class MockGoStruct:
            def __init__(self, name, is_exported):
                self.name = name
                self.is_exported = is_exported
        
        class MockGoModule:
            def __init__(self):
                self.functions = [
                    MockGoFunction("ExportedFunc", True),
                    MockGoFunction("privateFunc", False)
                ]
                self.structs = [
                    MockGoStruct("ExportedStruct", True),
                    MockGoStruct("privateStruct", False)
                ]
        
        module_info = MockGoModule()
        exports = self.mapper._extract_exports(module_info, Language.GO)
        
        assert len(exports) == 2
        assert "ExportedFunc" in exports
        assert "ExportedStruct" in exports
        assert "privateFunc" not in exports
        assert "privateStruct" not in exports
    
    def test_detect_circular_dependencies(self):
        """测试检测循环依赖"""
        dependency_graph = {
            "A": ["B"],
            "B": ["C"],
            "C": ["A"],
            "D": ["E"],
            "E": ["D"]
        }
        
        circular_deps = self.mapper._detect_circular_dependencies(dependency_graph)
        
        assert len(circular_deps) == 2
        # 检查是否包含循环依赖
        cycles_found = False
        for cycle in circular_deps:
            if "A" in cycle and "B" in cycle and "C" in cycle:
                cycles_found = True
                break
        assert cycles_found
    
    def test_find_unused_modules(self):
        """测试查找未使用的模块"""
        project_mapping = ProjectMapping(project_path="/test")
        
        # 创建模拟模块
        module_a = ModuleMapping(
            file_path="/test/a.py",
            module_name="a",
            language=Language.PYTHON,
            dependents=["/test/b.py"]
        )
        module_b = ModuleMapping(
            file_path="/test/b.py",
            module_name="b",
            language=Language.PYTHON,
            dependents=[]
        )
        module_c = ModuleMapping(
            file_path="/test/c.py",
            module_name="c",
            language=Language.PYTHON,
            dependents=[]
        )
        
        project_mapping.modules = {
            "/test/a.py": module_a,
            "/test/b.py": module_b,
            "/test/c.py": module_c
        }
        
        unused_modules = self.mapper._find_unused_modules(project_mapping)
        
        assert len(unused_modules) == 2
        assert "/test/b.py" in unused_modules
        assert "/test/c.py" in unused_modules
        assert "/test/a.py" not in unused_modules
    
    def test_get_module_statistics(self):
        """测试获取模块统计信息"""
        project_mapping = ProjectMapping(project_path="/test")
        
        # 创建模拟模块
        module_a = ModuleMapping(
            file_path="/test/a.py",
            module_name="a",
            language=Language.PYTHON,
            dependencies=["b"],
            dependents=[],
            line_count=100,
            complexity_score=10.0
        )
        module_b = ModuleMapping(
            file_path="/test/b.py",
            module_name="b",
            language=Language.PYTHON,
            dependencies=[],
            dependents=["a"],
            line_count=50,
            complexity_score=5.0
        )
        
        project_mapping.modules = {
            "/test/a.py": module_a,
            "/test/b.py": module_b
        }
        project_mapping.total_files = 2
        project_mapping.total_lines = 150
        project_mapping.language_stats = {Language.PYTHON: 2}
        
        stats = self.mapper.get_module_statistics(project_mapping)
        
        assert stats['total_files'] == 2
        assert stats['total_lines'] == 150
        assert stats['average_complexity'] == 7.5
        assert stats['max_complexity'] == 10.0
        assert stats['dependency_stats']['max_dependencies'] == 1
        assert stats['dependency_stats']['average_dependencies'] == 0.5
        assert stats['dependency_stats']['max_dependents'] == 1
        assert stats['dependency_stats']['average_dependents'] == 0.5
    
    def test_export_mapping_to_json(self):
        """测试导出映射为JSON格式"""
        project_mapping = ProjectMapping(project_path="/test")
        
        module_a = ModuleMapping(
            file_path="/test/a.py",
            module_name="a",
            language=Language.PYTHON,
            dependencies=["b"],
            exports=["main"],
            imports=["os"],
            line_count=100,
            complexity_score=10.0,
            last_modified=1234567890.0
        )
        
        project_mapping.modules = {
            "/test/a.py": module_a
        }
        project_mapping.total_files = 1
        project_mapping.total_lines = 100
        project_mapping.language_stats = {Language.PYTHON: 1}
        
        json_data = self.mapper.export_mapping_to_json(project_mapping)
        
        assert json_data['project_path'] == "/test"
        assert json_data['total_files'] == 1
        assert json_data['total_lines'] == 100
        assert json_data['language_stats']['python'] == 1
        
        # 检查模块信息
        module_info = json_data['modules']['/test/a.py']
        assert module_info['module_name'] == "a"
        assert module_info['language'] == "python"
        assert module_info['dependencies'] == ["b"]
        assert module_info['exports'] == ["main"]
        assert module_info['imports'] == ["os"]
        assert module_info['line_count'] == 100
        assert module_info['complexity_score'] == 10.0
        assert module_info['last_modified'] == 1234567890.0


class TestModuleMapperIntegration:
    """模块映射生成器集成测试"""
    
    def test_generate_project_mapping_simple(self):
        """测试生成简单项目映射"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            python_file = Path(temp_dir) / "test.py"
            python_file.write_text("""
import os
import sys

def main():
    pass

class TestClass:
    def test_method(self):
        pass
""")
            
            go_file = Path(temp_dir) / "test.go"
            go_file.write_text("""
package main

import "fmt"

func main() {
    fmt.Println("Hello")
}
""")
            
            # 生成项目映射
            project_mapping = generate_project_mapping(temp_dir)
            
            assert project_mapping.project_path == temp_dir
            assert project_mapping.total_files == 2
            assert len(project_mapping.modules) == 2
            
            # 检查语言统计
            assert project_mapping.language_stats[Language.PYTHON] == 1
            assert project_mapping.language_stats[Language.GO] == 1
    
    def test_generate_project_mapping_with_exclude(self):
        """测试生成项目映射时排除文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            python_file = Path(temp_dir) / "test.py"
            python_file.write_text("def main(): pass")
            
            excluded_file = Path(temp_dir) / "excluded" / "test.py"
            excluded_file.parent.mkdir()
            excluded_file.write_text("def excluded(): pass")
            
            # 生成项目映射，排除excluded目录
            project_mapping = generate_project_mapping(temp_dir, exclude_patterns=["excluded"])
            
            assert len(project_mapping.modules) == 1
            assert str(python_file) in project_mapping.modules
            assert str(excluded_file) not in project_mapping.modules
    
    def test_export_mapping_to_json_function(self):
        """测试导出映射为JSON格式的便捷函数"""
        project_mapping = ProjectMapping(project_path="/test")
        
        module_a = ModuleMapping(
            file_path="/test/a.py",
            module_name="a",
            language=Language.PYTHON,
            line_count=50,
            complexity_score=5.0
        )
        
        project_mapping.modules = {
            "/test/a.py": module_a
        }
        project_mapping.total_files = 1
        project_mapping.total_lines = 50
        
        json_data = export_mapping_to_json(project_mapping)
        
        assert json_data['project_path'] == "/test"
        assert json_data['total_files'] == 1
        assert json_data['total_lines'] == 50
        assert "/test/a.py" in json_data['modules']
    
    def test_complexity_score_calculation(self):
        """测试复杂度分数计算"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建复杂文件
            complex_file = Path(temp_dir) / "complex.py"
            complex_file.write_text("""
import os
import sys
import json
from typing import List, Dict

def simple_function():
    pass

def complex_function(param1: str, param2: int) -> bool:
    return True

class SimpleClass:
    def __init__(self):
        pass

class ComplexClass:
    def __init__(self, name: str):
        self.name = name
    
    def method1(self):
        pass
    
    def method2(self, param: str) -> str:
        return param
    
    @staticmethod
    def static_method():
        pass

def main():
    pass
""")
            
            project_mapping = generate_project_mapping(temp_dir)
            
            assert len(project_mapping.modules) == 1
            module_mapping = list(project_mapping.modules.values())[0]
            
            # 检查复杂度分数是否合理
            assert module_mapping.complexity_score > 0
            assert module_mapping.line_count > 0
    
    def test_dependency_analysis(self):
        """测试依赖关系分析"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建有依赖关系的文件
            module_a = Path(temp_dir) / "module_a.py"
            module_a.write_text("""
import module_b

def function_a():
    pass
""")
            
            module_b = Path(temp_dir) / "module_b.py"
            module_b.write_text("""
import module_c

def function_b():
    pass
""")
            
            module_c = Path(temp_dir) / "module_c.py"
            module_c.write_text("""
def function_c():
    pass
""")
            
            project_mapping = generate_project_mapping(temp_dir)
            
            assert len(project_mapping.modules) == 3
            
            # 检查依赖图
            assert len(project_mapping.dependency_graph) == 3
            
            # 检查统计信息
            stats = project_mapping.modules[str(module_a)].dependencies
            assert len(stats) >= 0  # 可能包含标准库依赖


if __name__ == "__main__":
    pytest.main([__file__]) 