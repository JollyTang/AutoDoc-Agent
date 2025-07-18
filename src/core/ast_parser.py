"""
Python代码AST解析器

使用libcst库解析Python代码，提取模块、类、函数等信息。
"""

import ast
import libcst as cst
from libcst.metadata import MetadataWrapper, QualifiedNameProvider, ParentNodeProvider, PositionProvider
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging

from .language_detector import Language, detect_language

logger = logging.getLogger(__name__)


@dataclass
class FunctionInfo:
    """函数信息"""
    name: str
    line_number: int
    end_line: int
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    is_async: bool = False
    is_method: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False


@dataclass
class ClassInfo:
    """类信息"""
    name: str
    line_number: int
    end_line: int
    docstring: Optional[str] = None
    bases: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    class_variables: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)


@dataclass
class ModuleInfo:
    """模块信息"""
    name: str
    file_path: str
    docstring: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    from_imports: List[str] = field(default_factory=list)
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    constants: List[str] = field(default_factory=list)
    line_count: int = 0
    language: Language = Language.PYTHON


class PythonASTParser:
    """
    Python代码AST解析器
    
    使用libcst库解析Python代码，提取详细的代码结构信息。
    """
    
    def __init__(self):
        """初始化AST解析器"""
        self.visitor = None
    
    def parse_file(self, file_path: str) -> Optional[ModuleInfo]:
        """
        解析Python文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            模块信息，如果解析失败则返回None
        """
        try:
            # 检查文件语言
            language = detect_language(file_path)
            if language != Language.PYTHON:
                logger.warning(f"文件 {file_path} 不是Python文件")
                return None
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # 解析AST
            return self.parse_source(source_code, file_path)
            
        except Exception as e:
            logger.error(f"解析文件 {file_path} 时出错: {e}")
            return None
    
    def parse_source(self, source_code: str, file_path: str = "<string>") -> Optional[ModuleInfo]:
        """
        解析Python源代码
        
        Args:
            source_code: 源代码字符串
            file_path: 文件路径（用于标识）
            
        Returns:
            模块信息，如果解析失败则返回None
        """
        try:
            # 创建CST树
            tree = cst.parse_module(source_code)
            
            # 创建元数据包装器
            wrapper = MetadataWrapper(tree)
            
            # 创建访问者
            visitor = PythonASTVisitor()
            
            # 访问AST
            wrapper.visit(visitor)
            
            # 构建模块信息
            module_info = ModuleInfo(
                name=Path(file_path).stem,
                file_path=file_path,
                docstring=visitor.module_docstring,
                imports=visitor.imports,
                from_imports=visitor.from_imports,
                functions=visitor.functions,
                classes=visitor.classes,
                variables=visitor.variables,
                constants=visitor.constants,
                line_count=len(source_code.splitlines()),
                language=Language.PYTHON
            )
            
            return module_info
            
        except Exception as e:
            logger.error(f"解析源代码时出错: {e}")
            return None
    
    def parse_directory(self, directory: str, 
                       exclude_patterns: Optional[List[str]] = None) -> Dict[str, ModuleInfo]:
        """
        解析目录中的所有Python文件
        
        Args:
            directory: 目录路径
            exclude_patterns: 排除的文件模式列表
            
        Returns:
            文件路径到模块信息的映射
        """
        if exclude_patterns is None:
            exclude_patterns = []
        
        results = {}
        
        try:
            for file_path in Path(directory).rglob("*.py"):
                # 排除隐藏目录
                if any(part.startswith('.') for part in file_path.parts):
                    continue
                
                file_path_str = str(file_path)
                
                # 检查排除模式
                if any(pattern in file_path_str for pattern in exclude_patterns):
                    continue
                
                module_info = self.parse_file(file_path_str)
                if module_info:
                    results[file_path_str] = module_info
                    
        except Exception as e:
            logger.error(f"解析目录 {directory} 时出错: {e}")
        
        return results


class PythonASTVisitor(cst.CSTVisitor):
    """
    Python AST访问者
    
    遍历CST树，提取代码结构信息。
    """
    
    METADATA_DEPENDENCIES = (QualifiedNameProvider, ParentNodeProvider, PositionProvider)
    
    def __init__(self):
        """初始化访问者"""
        super().__init__()
        self.module_docstring: Optional[str] = None
        self.imports: List[str] = []
        self.from_imports: List[str] = []
        self.functions: List[FunctionInfo] = []
        self.classes: List[ClassInfo] = []
        self.variables: List[str] = []
        self.constants: List[str] = []
        self._current_class: Optional[ClassInfo] = None
        self._current_function: Optional[FunctionInfo] = None
    
    def visit_Module(self, node: cst.Module) -> bool:
        """访问模块节点"""
        # 提取模块文档字符串
        if node.body and isinstance(node.body[0], cst.SimpleStatementLine):
            stmt = node.body[0].body[0]
            if isinstance(stmt, cst.Expr) and isinstance(stmt.value, cst.SimpleString):
                docstring = stmt.value.value.strip('"\'')
                # 清理文档字符串格式
                docstring = docstring.strip()
                self.module_docstring = docstring
        return True
    
    def visit_Import(self, node: cst.Import) -> bool:
        """访问import语句"""
        for alias in node.names:
            if isinstance(alias.name, cst.Name):
                self.imports.append(alias.name.value)
            elif isinstance(alias.name, cst.Attribute):
                # 处理类似 import os.path 的情况
                name_parts = []
                current = alias.name
                while isinstance(current, cst.Attribute):
                    name_parts.insert(0, current.attr.value)
                    current = current.value
                if isinstance(current, cst.Name):
                    name_parts.insert(0, current.value)
                self.imports.append('.'.join(name_parts))
        return True
    
    def visit_ImportFrom(self, node: cst.ImportFrom) -> bool:
        """访问from import语句"""
        module_name = ""
        if node.module:
            if isinstance(node.module, cst.Name):
                module_name = node.module.value
            elif isinstance(node.module, cst.Attribute):
                # 处理相对导入
                name_parts = []
                current = node.module
                while isinstance(current, cst.Attribute):
                    name_parts.insert(0, current.attr.value)
                    current = current.value
                if isinstance(current, cst.Name):
                    name_parts.insert(0, current.value)
                module_name = '.'.join(name_parts)
        
        for alias in node.names:
            if isinstance(alias.name, cst.Name):
                self.from_imports.append(f"{module_name}.{alias.name.value}")
        return True
    
    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:
        """访问函数定义"""
        # 获取位置信息
        position = self.get_metadata(PositionProvider, node)
        start_line = position.start.line if position else 1
        end_line = position.end.line if position else start_line
        
        # 检查是否为异步函数
        # 在libcst中，异步函数也是FunctionDef，但会有async关键字
        # 我们可以通过检查原始代码来判断
        is_async = False
        try:
            # 获取原始代码片段来判断是否有async关键字
            if hasattr(node, 'header') and hasattr(node.header, 'async_keyword'):
                is_async = node.header.async_keyword is not None
        except:
            pass
        
        # 提取函数信息
        function_info = FunctionInfo(
            name=node.name.value,
            line_number=start_line,
            end_line=end_line,
            is_async=is_async,
            is_method=self._current_class is not None
        )
        
        # 提取文档字符串
        if node.body.body and isinstance(node.body.body[0], cst.SimpleStatementLine):
            stmt = node.body.body[0].body[0]
            if isinstance(stmt, cst.Expr) and isinstance(stmt.value, cst.SimpleString):
                docstring = stmt.value.value.strip('"\'')
                # 清理文档字符串格式
                docstring = docstring.strip()
                function_info.docstring = docstring
        
        # 提取参数
        function_info.parameters = self._extract_parameters(node.params)
        
        # 提取返回类型注解
        if node.returns:
            function_info.return_type = self._extract_type_annotation(node.returns)
        
        # 提取装饰器
        function_info.decorators = self._extract_decorators(node.decorators)
        
        # 检查是否为类方法或静态方法
        for decorator in function_info.decorators:
            if 'classmethod' in decorator:
                function_info.is_classmethod = True
            elif 'staticmethod' in decorator:
                function_info.is_staticmethod = True
        
        # 添加到相应的列表
        if self._current_class:
            self._current_class.methods.append(function_info)
        else:
            # 只添加顶级函数，不添加嵌套函数
            self.functions.append(function_info)
        
        # 继续访问函数体，但不添加嵌套函数到顶级函数列表
        return True
    
    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        """访问类定义"""
        # 获取位置信息
        position = self.get_metadata(PositionProvider, node)
        start_line = position.start.line if position else 1
        end_line = position.end.line if position else start_line
        
        # 创建类信息
        class_info = ClassInfo(
            name=node.name.value,
            line_number=start_line,
            end_line=end_line
        )
        
        # 提取文档字符串
        if node.body.body and isinstance(node.body.body[0], cst.SimpleStatementLine):
            stmt = node.body.body[0].body[0]
            if isinstance(stmt, cst.Expr) and isinstance(stmt.value, cst.SimpleString):
                docstring = stmt.value.value.strip('"\'')
                # 清理文档字符串格式
                docstring = docstring.strip()
                class_info.docstring = docstring
        
        # 提取基类
        for base in node.bases:
            class_info.bases.append(self._extract_name(base.value))
        
        # 提取装饰器
        class_info.decorators = self._extract_decorators(node.decorators)
        
        # 保存当前类上下文
        previous_class = self._current_class
        self._current_class = class_info
        
        # 访问类体 - 使用正确的方式
        for item in node.body.body:
            if isinstance(item, cst.SimpleStatementLine):
                for stmt in item.body:
                    if isinstance(stmt, cst.FunctionDef):
                        self.visit_FunctionDef(stmt)
            elif isinstance(item, cst.FunctionDef):
                self.visit_FunctionDef(item)
        
        # 恢复上下文
        self._current_class = previous_class
        
        # 添加到类列表
        self.classes.append(class_info)
        
        return False  # 已经手动访问了类体
    
    def visit_Assign(self, node: cst.Assign) -> bool:
        """访问赋值语句"""
        for target in node.targets:
            if isinstance(target.target, cst.Name):
                var_name = target.target.value
                # 检查是否为常量（全大写）
                if var_name.isupper():
                    self.constants.append(var_name)
                else:
                    self.variables.append(var_name)
        return True
    
    def visit_AnnAssign(self, node: cst.AnnAssign) -> bool:
        """访问类型注解赋值语句"""
        if isinstance(node.target, cst.Name):
            var_name = node.target.value
            if var_name.isupper():
                self.constants.append(var_name)
            else:
                self.variables.append(var_name)
        return True
    
    def _extract_parameters(self, params: cst.Parameters) -> List[str]:
        """提取函数参数"""
        parameters = []
        
        # 位置参数
        for param in params.posonly_params:
            parameters.append(param.name.value)
        
        # 普通参数
        for param in params.params:
            parameters.append(param.name.value)
        
        # 仅关键字参数
        for param in params.kwonly_params:
            parameters.append(param.name.value)
        
        return parameters
    
    def _extract_type_annotation(self, annotation: cst.Annotation) -> str:
        """提取类型注解"""
        return self._extract_name(annotation.annotation)
    
    def _extract_decorators(self, decorators: List[cst.Decorator]) -> List[str]:
        """提取装饰器"""
        decorator_names = []
        for decorator in decorators:
            decorator_names.append(self._extract_name(decorator.decorator))
        return decorator_names
    
    def _extract_name(self, node: cst.BaseExpression) -> str:
        """提取节点名称"""
        if isinstance(node, cst.Name):
            return node.value
        elif isinstance(node, cst.Attribute):
            return f"{self._extract_name(node.value)}.{node.attr.value}"
        elif isinstance(node, cst.Subscript):
            return self._extract_name(node.value)
        elif hasattr(cst, 'Constant') and isinstance(node, cst.Constant):
            # 处理常量，如None
            if node.value is None:
                return "None"
            return str(node.value)
        elif hasattr(cst, 'Name') and isinstance(node, cst.Name) and node.value == 'None':
            # 处理None作为Name的情况
            return "None"
        else:
            return str(node)


# 便捷函数
def parse_python_file(file_path: str) -> Optional[ModuleInfo]:
    """
    解析Python文件（便捷函数）
    
    Args:
        file_path: 文件路径
        
    Returns:
        模块信息
    """
    parser = PythonASTParser()
    return parser.parse_file(file_path)


def parse_python_source(source_code: str, file_path: str = "<string>") -> Optional[ModuleInfo]:
    """
    解析Python源代码（便捷函数）
    
    Args:
        source_code: 源代码字符串
        file_path: 文件路径
        
    Returns:
        模块信息
    """
    parser = PythonASTParser()
    return parser.parse_source(source_code, file_path)


def parse_python_directory(directory: str, 
                          exclude_patterns: Optional[List[str]] = None) -> Dict[str, ModuleInfo]:
    """
    解析目录中的所有Python文件（便捷函数）
    
    Args:
        directory: 目录路径
        exclude_patterns: 排除的文件模式列表
        
    Returns:
        文件路径到模块信息的映射
    """
    parser = PythonASTParser()
    return parser.parse_directory(directory, exclude_patterns) 