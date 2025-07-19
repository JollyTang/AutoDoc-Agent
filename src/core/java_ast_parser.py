"""
Java代码AST解析器

使用tree-sitter库解析Java代码，提取类、方法、字段等信息。
"""

import ast
import re
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging

try:
    from tree_sitter import Language, Parser, Node
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    Node = Any

from .language_detector import Language as LanguageEnum, detect_language

logger = logging.getLogger(__name__)


@dataclass
class JavaMethodInfo:
    """Java方法信息"""
    name: str
    line_number: int
    end_line: int
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    parameter_types: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    modifiers: List[str] = field(default_factory=list)
    is_constructor: bool = False
    is_static: bool = False
    is_abstract: bool = False
    is_final: bool = False
    is_public: bool = False
    is_private: bool = False
    is_protected: bool = False
    throws_exceptions: List[str] = field(default_factory=list)


@dataclass
class JavaFieldInfo:
    """Java字段信息"""
    name: str
    line_number: int
    end_line: int
    field_type: str
    docstring: Optional[str] = None
    modifiers: List[str] = field(default_factory=list)
    is_static: bool = False
    is_final: bool = False
    is_public: bool = False
    is_private: bool = False
    is_protected: bool = False
    initial_value: Optional[str] = None


@dataclass
class JavaClassInfo:
    """Java类信息"""
    name: str
    line_number: int
    end_line: int
    docstring: Optional[str] = None
    package_name: Optional[str] = None
    superclass: Optional[str] = None
    interfaces: List[str] = field(default_factory=list)
    methods: List[JavaMethodInfo] = field(default_factory=list)
    fields: List[JavaFieldInfo] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    is_interface: bool = False
    is_abstract: bool = False
    is_final: bool = False
    is_public: bool = False
    is_private: bool = False
    is_protected: bool = False


@dataclass
class JavaModuleInfo:
    """Java模块信息"""
    name: str
    file_path: str
    package_name: Optional[str] = None
    docstring: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    classes: List[JavaClassInfo] = field(default_factory=list)
    interfaces: List[JavaClassInfo] = field(default_factory=list)
    enums: List[JavaClassInfo] = field(default_factory=list)
    line_count: int = 0
    language: LanguageEnum = LanguageEnum.JAVA


class JavaASTParser:
    """
    Java代码AST解析器
    
    使用tree-sitter库解析Java代码，提取详细的代码结构信息。
    """
    
    def __init__(self):
        """初始化AST解析器"""
        self.parser = None
        self.language = None
        
        if TREE_SITTER_AVAILABLE:
            self._init_tree_sitter()
    
    def _init_tree_sitter(self):
        """初始化tree-sitter解析器"""
        try:
            # 尝试加载Java语言库
            # 注意：这里需要正确的tree-sitter Java语言库路径
            # 由于我们没有安装tree-sitter Java库，这里会失败
            # 在实际使用中需要先安装：pip install tree-sitter-java
            self.language = Language('java', 'java')
            self.parser = Parser()
            self.parser.set_language(self.language)
        except Exception as e:
            logger.warning(f"无法初始化tree-sitter Java解析器: {e}")
            self.parser = None
    
    def parse_file(self, file_path: str) -> Optional[JavaModuleInfo]:
        """
        解析Java文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            模块信息，如果解析失败则返回None
        """
        try:
            # 检查文件语言
            language = detect_language(file_path)
            if language != LanguageEnum.JAVA:
                logger.warning(f"文件 {file_path} 不是Java文件")
                return None
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # 解析AST，使用原始文件路径
            return self.parse_source(source_code, file_path)
            
        except Exception as e:
            logger.error(f"解析文件 {file_path} 时出错: {e}")
            return None
    
    def parse_source(self, source_code: str, file_path: str = "<string>") -> Optional[JavaModuleInfo]:
        """
        解析Java源代码
        
        Args:
            source_code: 源代码字符串
            file_path: 文件路径（用于标识）
            
        Returns:
            模块信息，如果解析失败则返回None
        """
        try:
            if TREE_SITTER_AVAILABLE and self.parser:
                return self._parse_with_tree_sitter(source_code, file_path)
            else:
                return self._parse_with_regex(source_code, file_path)
                
        except Exception as e:
            logger.error(f"解析源代码时出错: {e}")
            return None
    
    def _parse_with_tree_sitter(self, source_code: str, file_path: str) -> Optional[JavaModuleInfo]:
        """使用tree-sitter解析"""
        try:
            tree = self.parser.parse(bytes(source_code, 'utf8'))
            visitor = JavaASTVisitor()
            visitor.visit(tree.root_node)
            
            return JavaModuleInfo(
                name=Path(file_path).stem,
                file_path=file_path,
                package_name=visitor.package_name,
                docstring=visitor.module_docstring,
                imports=visitor.imports,
                classes=visitor.classes,
                interfaces=visitor.interfaces,
                enums=visitor.enums,
                line_count=len(source_code.splitlines()),
                language=LanguageEnum.JAVA
            )
        except Exception as e:
            logger.error(f"Tree-sitter解析失败: {e}")
            return self._parse_with_regex(source_code, file_path)
    
    def _parse_with_regex(self, source_code: str, file_path: str) -> Optional[JavaModuleInfo]:
        """使用正则表达式解析（备用方案）"""
        try:
            lines = source_code.splitlines()
            
            # 提取包名
            package_match = re.search(r'package\s+([\w.]+);', source_code)
            package_name = package_match.group(1) if package_match else None
            
            # 提取导入语句
            imports = []
            import_pattern = r'import\s+(?:static\s+)?([\w.*]+);'
            for match in re.finditer(import_pattern, source_code):
                imports.append(match.group(1))
            
            # 提取类定义
            classes = []
            class_pattern = r'(?:public\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\s,]+))?\s*\{'
            for match in re.finditer(class_pattern, source_code):
                class_name = match.group(1)
                superclass = match.group(2)
                interfaces_str = match.group(3)
                
                interfaces = []
                if interfaces_str:
                    interfaces = [i.strip() for i in interfaces_str.split(',')]
                
                # 提取修饰符
                modifiers = []
                if 'public' in match.group(0):
                    modifiers.append('public')
                if 'abstract' in match.group(0):
                    modifiers.append('abstract')
                if 'final' in match.group(0):
                    modifiers.append('final')
                
                # 简单的类信息
                class_info = JavaClassInfo(
                    name=class_name,
                    line_number=1,  # 简化处理
                    end_line=len(lines),
                    superclass=superclass,
                    interfaces=interfaces,
                    modifiers=modifiers,
                    is_public='public' in modifiers,
                    is_abstract='abstract' in modifiers,
                    is_final='final' in modifiers
                )
                
                # 提取类中的方法和字段
                self._extract_class_members(source_code, class_info)
                classes.append(class_info)
            
            # 提取接口定义
            interfaces = []
            interface_pattern = r'(?:public\s+)?interface\s+(\w+)(?:\s+extends\s+([\w\s,]+))?\s*\{'
            for match in re.finditer(interface_pattern, source_code):
                interface_name = match.group(1)
                extends_str = match.group(2)
                
                extends_interfaces = []
                if extends_str:
                    extends_interfaces = [i.strip() for i in extends_str.split(',')]
                
                # 提取修饰符
                modifiers = []
                if 'public' in match.group(0):
                    modifiers.append('public')
                
                interface_info = JavaClassInfo(
                    name=interface_name,
                    line_number=1,
                    end_line=len(lines),
                    interfaces=extends_interfaces,
                    modifiers=modifiers,
                    is_interface=True,
                    is_public='public' in modifiers
                )
                
                # 提取接口中的方法
                self._extract_interface_methods(source_code, interface_info)
                interfaces.append(interface_info)
            
            # 提取枚举定义
            enums = []
            enum_pattern = r'(?:public\s+)?enum\s+(\w+)(?:\s+implements\s+([\w\s,]+))?\s*\{'
            for match in re.finditer(enum_pattern, source_code):
                enum_name = match.group(1)
                implements_str = match.group(2)
                
                implements_interfaces = []
                if implements_str:
                    implements_interfaces = [i.strip() for i in implements_str.split(',')]
                
                # 提取修饰符
                modifiers = []
                if 'public' in match.group(0):
                    modifiers.append('public')
                
                enum_info = JavaClassInfo(
                    name=enum_name,
                    line_number=1,
                    end_line=len(lines),
                    interfaces=implements_interfaces,
                    modifiers=modifiers,
                    is_public='public' in modifiers
                )
                
                # 提取枚举中的方法
                self._extract_enum_methods(source_code, enum_info)
                enums.append(enum_info)
            
            # 使用正确的文件名
            module_name = Path(file_path).stem if file_path != "<string>" else "Unknown"
            
            return JavaModuleInfo(
                name=module_name,
                file_path=file_path,
                package_name=package_name,
                imports=imports,
                classes=classes,
                interfaces=interfaces,
                enums=enums,
                line_count=len(lines),
                language=LanguageEnum.JAVA
            )
            
        except Exception as e:
            logger.error(f"正则表达式解析失败: {e}")
            return None
    
    def _extract_class_members(self, source_code: str, class_info: JavaClassInfo):
        """提取类中的方法和字段"""
        # 提取方法 - 包括抽象方法
        method_pattern = r'(?:public|private|protected|static|final|abstract|synchronized|native|strictfp)?\s*(?:public|private|protected)?\s*(?:static|final|abstract|synchronized|native|strictfp)?\s*(?:<[^>]+>\s*)?(\w+(?:<[^>]+>)?)\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[^{]+)?\s*(?:\{|;)'
        for match in re.finditer(method_pattern, source_code):
            return_type = match.group(1)
            method_name = match.group(2)
            
            # 检查是否为构造函数
            is_constructor = method_name == class_info.name
            
            # 提取修饰符
            modifiers = []
            method_text = match.group(0)
            if 'public' in method_text:
                modifiers.append('public')
            if 'private' in method_text:
                modifiers.append('private')
            if 'protected' in method_text:
                modifiers.append('protected')
            if 'static' in method_text:
                modifiers.append('static')
            if 'final' in method_text:
                modifiers.append('final')
            if 'abstract' in method_text:
                modifiers.append('abstract')
            
            # 提取参数
            params_match = re.search(r'\(([^)]*)\)', method_text)
            parameters = []
            parameter_types = []
            if params_match and params_match.group(1).strip():
                params_str = params_match.group(1)
                for param in params_str.split(','):
                    param = param.strip()
                    if param:
                        # 简单的参数解析
                        parts = param.split()
                        if len(parts) >= 2:
                            param_type = parts[0]
                            param_name = parts[1]
                            parameters.append(param_name)
                            parameter_types.append(param_type)
            
            # 提取异常声明
            throws_exceptions = []
            throws_match = re.search(r'throws\s+([^{]+)', method_text)
            if throws_match:
                throws_str = throws_match.group(1).strip()
                throws_exceptions = [e.strip() for e in throws_str.split(',')]
            
            method_info = JavaMethodInfo(
                name=method_name,
                line_number=1,
                end_line=1,
                return_type=return_type if not is_constructor else None,
                parameters=parameters,
                parameter_types=parameter_types,
                modifiers=modifiers,
                is_constructor=is_constructor,
                is_public='public' in modifiers,
                is_private='private' in modifiers,
                is_protected='protected' in modifiers,
                is_static='static' in modifiers,
                is_abstract='abstract' in modifiers,
                is_final='final' in modifiers,
                throws_exceptions=throws_exceptions
            )
            class_info.methods.append(method_info)
        
        # 提取字段 - 改进正则表达式以更好地处理修饰符
        # 修复正则表达式以正确匹配开头的修饰符
        field_pattern = r'(?:public|private|protected)?\s*(?:static|final|transient|volatile)?\s*(?:static|final|transient|volatile)?\s*(\w+(?:<[^>]+>)?)\s+(\w+)\s*(?:=\s*[^;]+)?;'
        for match in re.finditer(field_pattern, source_code):
            field_type = match.group(1)
            field_name = match.group(2)
            
            # 提取修饰符 - 改进修饰符检测
            modifiers = []
            field_text = match.group(0)
            
            # 检查访问修饰符 - 修复private检测
            if 'private' in field_text:
                modifiers.append('private')
            elif 'public' in field_text:
                modifiers.append('public')
            elif 'protected' in field_text:
                modifiers.append('protected')
            
            # 检查其他修饰符
            if 'static' in field_text:
                modifiers.append('static')
            if 'final' in field_text:
                modifiers.append('final')
            if 'transient' in field_text:
                modifiers.append('transient')
            if 'volatile' in field_text:
                modifiers.append('volatile')
            
            field_info = JavaFieldInfo(
                name=field_name,
                line_number=1,
                end_line=1,
                field_type=field_type,
                modifiers=modifiers,
                is_public='public' in modifiers,
                is_private='private' in modifiers,
                is_protected='protected' in modifiers,
                is_static='static' in modifiers,
                is_final='final' in modifiers
            )
            class_info.fields.append(field_info)
    
    def _extract_interface_methods(self, source_code: str, interface_info: JavaClassInfo):
        """提取接口中的方法"""
        # 接口方法模式（包括默认方法）
        method_pattern = r'(?:public|private|static|default|abstract)?\s*(?:public|private|static|default|abstract)?\s*(?:<[^>]+>\s*)?(\w+(?:<[^>]+>)?)\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[^{]+)?\s*(?:\{|;)'
        for match in re.finditer(method_pattern, source_code):
            return_type = match.group(1)
            method_name = match.group(2)
            
            # 提取修饰符
            modifiers = []
            method_text = match.group(0)
            if 'public' in method_text:
                modifiers.append('public')
            if 'private' in method_text:
                modifiers.append('private')
            if 'static' in method_text:
                modifiers.append('static')
            if 'default' in method_text:
                modifiers.append('default')
            if 'abstract' in method_text:
                modifiers.append('abstract')
            
            method_info = JavaMethodInfo(
                name=method_name,
                line_number=1,
                end_line=1,
                return_type=return_type,
                modifiers=modifiers,
                is_public='public' in modifiers,
                is_private='private' in modifiers,
                is_static='static' in modifiers,
                is_abstract='abstract' in modifiers
            )
            interface_info.methods.append(method_info)
    
    def _extract_enum_methods(self, source_code: str, enum_info: JavaClassInfo):
        """提取枚举中的方法"""
        # 枚举方法模式
        method_pattern = r'(?:public|private|protected|static|final|abstract)?\s*(?:public|private|protected)?\s*(?:static|final|abstract)?\s*(?:<[^>]+>\s*)?(\w+(?:<[^>]+>)?)\s+(\w+)\s*\([^)]*\)\s*(?:throws\s+[^{]+)?\s*\{'
        for match in re.finditer(method_pattern, source_code):
            return_type = match.group(1)
            method_name = match.group(2)
            
            # 提取修饰符
            modifiers = []
            method_text = match.group(0)
            if 'public' in method_text:
                modifiers.append('public')
            if 'private' in method_text:
                modifiers.append('private')
            if 'protected' in method_text:
                modifiers.append('protected')
            if 'static' in method_text:
                modifiers.append('static')
            if 'final' in method_text:
                modifiers.append('final')
            if 'abstract' in method_text:
                modifiers.append('abstract')
            
            method_info = JavaMethodInfo(
                name=method_name,
                line_number=1,
                end_line=1,
                return_type=return_type,
                modifiers=modifiers,
                is_public='public' in modifiers,
                is_private='private' in modifiers,
                is_protected='protected' in modifiers,
                is_static='static' in modifiers,
                is_final='final' in modifiers,
                is_abstract='abstract' in modifiers
            )
            enum_info.methods.append(method_info)
    
    def parse_directory(self, directory: str, 
                       exclude_patterns: Optional[List[str]] = None) -> Dict[str, JavaModuleInfo]:
        """
        解析目录中的所有Java文件
        
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
            for file_path in Path(directory).rglob("*.java"):
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


class JavaASTVisitor:
    """
    Java AST访问者
    
    遍历tree-sitter AST树，提取代码结构信息。
    """
    
    def __init__(self):
        """初始化访问者"""
        self.package_name: Optional[str] = None
        self.module_docstring: Optional[str] = None
        self.imports: List[str] = []
        self.classes: List[JavaClassInfo] = []
        self.interfaces: List[JavaClassInfo] = []
        self.enums: List[JavaClassInfo] = []
        self._current_class: Optional[JavaClassInfo] = None
        self._current_method: Optional[JavaMethodInfo] = None
        self._current_field: Optional[JavaFieldInfo] = None
    
    def visit(self, node: Node):
        """访问节点"""
        if node.type == 'package_declaration':
            self._visit_package_declaration(node)
        elif node.type == 'import_declaration':
            self._visit_import_declaration(node)
        elif node.type == 'class_declaration':
            self._visit_class_declaration(node)
        elif node.type == 'interface_declaration':
            self._visit_interface_declaration(node)
        elif node.type == 'enum_declaration':
            self._visit_enum_declaration(node)
        elif node.type == 'method_declaration':
            self._visit_method_declaration(node)
        elif node.type == 'field_declaration':
            self._visit_field_declaration(node)
        elif node.type == 'constructor_declaration':
            self._visit_constructor_declaration(node)
        
        # 递归访问子节点
        for child in node.children:
            self.visit(child)
    
    def _visit_package_declaration(self, node: Node):
        """访问包声明"""
        for child in node.children:
            if child.type == 'identifier':
                self.package_name = child.text.decode('utf8')
                break
    
    def _visit_import_declaration(self, node: Node):
        """访问导入声明"""
        import_text = node.text.decode('utf8').strip()
        if import_text.startswith('import'):
            # 移除 'import' 和 ';'
            import_name = import_text[6:].rstrip(';').strip()
            self.imports.append(import_name)
    
    def _visit_class_declaration(self, node: Node):
        """访问类声明"""
        class_info = self._create_class_info(node, is_interface=False)
        self.classes.append(class_info)
        
        # 保存当前类上下文
        previous_class = self._current_class
        self._current_class = class_info
        
        # 访问类体
        for child in node.children:
            if child.type == 'class_body':
                self.visit(child)
        
        # 恢复上下文
        self._current_class = previous_class
    
    def _visit_interface_declaration(self, node: Node):
        """访问接口声明"""
        interface_info = self._create_class_info(node, is_interface=True)
        self.interfaces.append(interface_info)
        
        # 保存当前类上下文
        previous_class = self._current_class
        self._current_class = interface_info
        
        # 访问接口体
        for child in node.children:
            if child.type == 'interface_body':
                self.visit(child)
        
        # 恢复上下文
        self._current_class = previous_class
    
    def _visit_enum_declaration(self, node: Node):
        """访问枚举声明"""
        enum_info = self._create_class_info(node, is_interface=False)
        self.enums.append(enum_info)
        
        # 保存当前类上下文
        previous_class = self._current_class
        self._current_class = enum_info
        
        # 访问枚举体
        for child in node.children:
            if child.type == 'enum_body':
                self.visit(child)
        
        # 恢复上下文
        self._current_class = previous_class
    
    def _visit_method_declaration(self, node: Node):
        """访问方法声明"""
        method_info = self._create_method_info(node, is_constructor=False)
        
        if self._current_class:
            self._current_class.methods.append(method_info)
    
    def _visit_constructor_declaration(self, node: Node):
        """访问构造函数声明"""
        method_info = self._create_method_info(node, is_constructor=True)
        
        if self._current_class:
            self._current_class.methods.append(method_info)
    
    def _visit_field_declaration(self, node: Node):
        """访问字段声明"""
        field_info = self._create_field_info(node)
        
        if self._current_class:
            self._current_class.fields.append(field_info)
    
    def _create_class_info(self, node: Node, is_interface: bool) -> JavaClassInfo:
        """创建类信息"""
        class_info = JavaClassInfo(
            name="",
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            is_interface=is_interface
        )
        
        # 提取类名
        for child in node.children:
            if child.type == 'identifier':
                class_info.name = child.text.decode('utf8')
                break
        
        # 提取修饰符
        class_info.modifiers = self._extract_modifiers(node)
        class_info.is_public = 'public' in class_info.modifiers
        class_info.is_private = 'private' in class_info.modifiers
        class_info.is_protected = 'protected' in class_info.modifiers
        class_info.is_abstract = 'abstract' in class_info.modifiers
        class_info.is_final = 'final' in class_info.modifiers
        
        # 提取继承信息
        for child in node.children:
            if child.type == 'superclass':
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        class_info.superclass = grandchild.text.decode('utf8')
                        break
            elif child.type == 'super_interfaces':
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        class_info.interfaces.append(grandchild.text.decode('utf8'))
        
        return class_info
    
    def _create_method_info(self, node: Node, is_constructor: bool) -> JavaMethodInfo:
        """创建方法信息"""
        method_info = JavaMethodInfo(
            name="",
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            is_constructor=is_constructor
        )
        
        # 提取方法名
        for child in node.children:
            if child.type == 'identifier':
                method_info.name = child.text.decode('utf8')
                break
        
        # 提取修饰符
        method_info.modifiers = self._extract_modifiers(node)
        method_info.is_public = 'public' in method_info.modifiers
        method_info.is_private = 'private' in method_info.modifiers
        method_info.is_protected = 'protected' in method_info.modifiers
        method_info.is_static = 'static' in method_info.modifiers
        method_info.is_abstract = 'abstract' in method_info.modifiers
        method_info.is_final = 'final' in method_info.modifiers
        
        # 提取参数
        for child in node.children:
            if child.type == 'formal_parameters':
                method_info.parameters, method_info.parameter_types = self._extract_parameters(child)
            elif child.type == 'type_identifier' and not is_constructor:
                method_info.return_type = child.text.decode('utf8')
            elif child.type == 'throws':
                method_info.throws_exceptions = self._extract_throws(child)
        
        return method_info
    
    def _create_field_info(self, node: Node) -> JavaFieldInfo:
        """创建字段信息"""
        field_info = JavaFieldInfo(
            name="",
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            field_type=""
        )
        
        # 提取字段类型和名称
        for child in node.children:
            if child.type == 'type_identifier':
                field_info.field_type = child.text.decode('utf8')
            elif child.type == 'variable_declarator':
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        field_info.name = grandchild.text.decode('utf8')
                        break
        
        # 提取修饰符
        field_info.modifiers = self._extract_modifiers(node)
        field_info.is_public = 'public' in field_info.modifiers
        field_info.is_private = 'private' in field_info.modifiers
        field_info.is_protected = 'protected' in field_info.modifiers
        field_info.is_static = 'static' in field_info.modifiers
        field_info.is_final = 'final' in field_info.modifiers
        
        return field_info
    
    def _extract_modifiers(self, node: Node) -> List[str]:
        """提取修饰符"""
        modifiers = []
        for child in node.children:
            if child.type in ['public', 'private', 'protected', 'static', 'final', 'abstract']:
                modifiers.append(child.type)
        return modifiers
    
    def _extract_parameters(self, node: Node) -> Tuple[List[str], List[str]]:
        """提取参数"""
        parameters = []
        parameter_types = []
        
        for child in node.children:
            if child.type == 'formal_parameter':
                param_name = ""
                param_type = ""
                
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        param_name = grandchild.text.decode('utf8')
                    elif grandchild.type == 'type_identifier':
                        param_type = grandchild.text.decode('utf8')
                
                if param_name:
                    parameters.append(param_name)
                    parameter_types.append(param_type)
        
        return parameters, parameter_types
    
    def _extract_throws(self, node: Node) -> List[str]:
        """提取抛出异常"""
        exceptions = []
        for child in node.children:
            if child.type == 'identifier':
                exceptions.append(child.text.decode('utf8'))
        return exceptions


# 便捷函数
def parse_java_file(file_path: str) -> Optional[JavaModuleInfo]:
    """
    解析Java文件（便捷函数）
    
    Args:
        file_path: 文件路径
        
    Returns:
        模块信息
    """
    parser = JavaASTParser()
    return parser.parse_file(file_path)


def parse_java_source(source_code: str, file_path: str = "<string>") -> Optional[JavaModuleInfo]:
    """
    解析Java源代码（便捷函数）
    
    Args:
        source_code: 源代码字符串
        file_path: 文件路径
        
    Returns:
        模块信息
    """
    parser = JavaASTParser()
    return parser.parse_source(source_code, file_path)


def parse_java_directory(directory: str, 
                        exclude_patterns: Optional[List[str]] = None) -> Dict[str, JavaModuleInfo]:
    """
    解析目录中的所有Java文件（便捷函数）
    
    Args:
        directory: 目录路径
        exclude_patterns: 排除的文件模式列表
        
    Returns:
        文件路径到模块信息的映射
    """
    parser = JavaASTParser()
    return parser.parse_directory(directory, exclude_patterns) 