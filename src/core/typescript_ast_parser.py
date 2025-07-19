"""
TypeScript代码AST解析器

使用tree-sitter库解析TypeScript代码，提取接口、类、函数等信息。
"""

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
class TypeScriptFunctionInfo:
    """TypeScript函数信息"""
    name: str
    line_number: int
    end_line: int
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    parameter_types: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    modifiers: List[str] = field(default_factory=list)
    is_async: bool = False
    is_method: bool = False
    is_static: bool = False
    is_private: bool = False
    is_protected: bool = False
    is_public: bool = False
    is_abstract: bool = False
    is_export: bool = False
    is_constructor: bool = False


@dataclass
class TypeScriptPropertyInfo:
    """TypeScript属性信息"""
    name: str
    line_number: int
    end_line: int
    property_type: str
    docstring: Optional[str] = None
    modifiers: List[str] = field(default_factory=list)
    is_static: bool = False
    is_readonly: bool = False
    is_optional: bool = False
    is_public: bool = False
    is_private: bool = False
    is_protected: bool = False
    is_export: bool = False
    initial_value: Optional[str] = None


@dataclass
class TypeScriptInterfaceInfo:
    """TypeScript接口信息"""
    name: str
    line_number: int
    end_line: int
    docstring: Optional[str] = None
    extends: List[str] = field(default_factory=list)
    properties: List[TypeScriptPropertyInfo] = field(default_factory=list)
    methods: List[TypeScriptFunctionInfo] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    is_export: bool = False


@dataclass
class TypeScriptClassInfo:
    """TypeScript类信息"""
    name: str
    line_number: int
    end_line: int
    docstring: Optional[str] = None
    extends: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    properties: List[TypeScriptPropertyInfo] = field(default_factory=list)
    methods: List[TypeScriptFunctionInfo] = field(default_factory=list)
    constructors: List[TypeScriptFunctionInfo] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    is_abstract: bool = False
    is_export: bool = False


@dataclass
class TypeScriptTypeInfo:
    """TypeScript类型定义信息"""
    name: str
    line_number: int
    end_line: int
    type_definition: str = ""
    docstring: Optional[str] = None
    modifiers: List[str] = field(default_factory=list)
    is_export: bool = False


@dataclass
class TypeScriptEnumInfo:
    """TypeScript枚举信息"""
    name: str
    line_number: int
    end_line: int
    docstring: Optional[str] = None
    members: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    is_export: bool = False


@dataclass
class TypeScriptModuleInfo:
    """TypeScript模块信息"""
    name: str
    file_path: str
    docstring: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    interfaces: List[TypeScriptInterfaceInfo] = field(default_factory=list)
    classes: List[TypeScriptClassInfo] = field(default_factory=list)
    functions: List[TypeScriptFunctionInfo] = field(default_factory=list)
    types: List[TypeScriptTypeInfo] = field(default_factory=list)
    enums: List[TypeScriptEnumInfo] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    constants: List[str] = field(default_factory=list)
    line_count: int = 0
    language: LanguageEnum = LanguageEnum.TYPESCRIPT


class TypeScriptASTParser:
    """
    TypeScript代码AST解析器
    
    使用tree-sitter库解析TypeScript代码，提取详细的代码结构信息。
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
            # 尝试加载TypeScript语言库
            # 注意：这里需要正确的tree-sitter TypeScript语言库路径
            # 由于我们没有安装tree-sitter TypeScript库，这里会失败
            # 在实际使用中需要先安装：pip install tree-sitter-typescript
            self.language = Language('typescript', 'typescript')
            self.parser = Parser()
            self.parser.set_language(self.language)
        except Exception as e:
            logger.warning(f"无法初始化tree-sitter TypeScript解析器: {e}")
            self.parser = None
    
    def parse_file(self, file_path: str) -> Optional[TypeScriptModuleInfo]:
        """
        解析TypeScript文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            模块信息，如果解析失败则返回None
        """
        try:
            # 检查文件语言
            language = detect_language(file_path)
            if language != LanguageEnum.TYPESCRIPT:
                logger.warning(f"文件 {file_path} 不是TypeScript文件")
                return None
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # 解析AST，使用原始文件路径
            return self.parse_source(source_code, file_path)
            
        except Exception as e:
            logger.error(f"解析文件 {file_path} 时出错: {e}")
            return None
    
    def parse_source(self, source_code: str, file_path: str = "<string>") -> Optional[TypeScriptModuleInfo]:
        """
        解析TypeScript源代码
        
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
    
    def _parse_with_tree_sitter(self, source_code: str, file_path: str) -> Optional[TypeScriptModuleInfo]:
        """使用tree-sitter解析"""
        try:
            tree = self.parser.parse(bytes(source_code, 'utf8'))
            visitor = TypeScriptASTVisitor()
            visitor.visit(tree.root_node)
            
            return TypeScriptModuleInfo(
                name=Path(file_path).stem,
                file_path=file_path,
                docstring=visitor.module_docstring,
                imports=visitor.imports,
                exports=visitor.exports,
                interfaces=visitor.interfaces,
                classes=visitor.classes,
                functions=visitor.functions,
                types=visitor.types,
                enums=visitor.enums,
                variables=visitor.variables,
                constants=visitor.constants,
                line_count=len(source_code.splitlines()),
                language=LanguageEnum.TYPESCRIPT
            )
        except Exception as e:
            logger.error(f"Tree-sitter解析失败: {e}")
            return self._parse_with_regex(source_code, file_path)
    
    def _parse_with_regex(self, source_code: str, file_path: str) -> Optional[TypeScriptModuleInfo]:
        """使用正则表达式解析（备用方案）"""
        try:
            lines = source_code.splitlines()
            
            # 提取导入语句
            imports = []
            import_pattern = r'import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+)?[\'"]([^\'"]+)[\'"];?'
            for match in re.finditer(import_pattern, source_code):
                imports.append(match.group(1))
            
            # 提取导出语句
            exports = []
            export_pattern = r'export\s+(?:default\s+)?(?:class|interface|function|const|let|var|type|enum)\s+(\w+)'
            for match in re.finditer(export_pattern, source_code):
                exports.append(match.group(1))
            
            # 提取接口定义
            interfaces = []
            interface_pattern = r'(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+([^{]+))?\s*\{'
            for match in re.finditer(interface_pattern, source_code):
                interface_name = match.group(1)
                extends_str = match.group(2)
                
                extends = []
                if extends_str:
                    extends = [e.strip() for e in extends_str.split(',')]
                
                # 提取修饰符
                modifiers = []
                if 'export' in match.group(0):
                    modifiers.append('export')
                
                interface_info = TypeScriptInterfaceInfo(
                    name=interface_name,
                    line_number=1,
                    end_line=len(lines),
                    extends=extends,
                    modifiers=modifiers,
                    is_export='export' in modifiers
                )
                
                # 提取接口中的属性和方法
                self._extract_interface_members(source_code, interface_info)
                interfaces.append(interface_info)
            
            # 提取类定义
            classes = []
            class_pattern = r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?\s*\{'
            for match in re.finditer(class_pattern, source_code):
                class_name = match.group(1)
                extends = match.group(2)
                implements_str = match.group(3)
                
                implements = []
                if implements_str:
                    implements = [i.strip() for i in implements_str.split(',')]
                
                # 提取修饰符
                modifiers = []
                if 'export' in match.group(0):
                    modifiers.append('export')
                if 'abstract' in match.group(0):
                    modifiers.append('abstract')
                
                class_info = TypeScriptClassInfo(
                    name=class_name,
                    line_number=1,
                    end_line=len(lines),
                    extends=extends,
                    implements=implements,
                    modifiers=modifiers,
                    is_abstract='abstract' in modifiers,
                    is_export='export' in modifiers
                )
                
                # 提取类中的属性和方法
                self._extract_class_members(source_code, class_info)
                classes.append(class_info)
            
            # 提取函数定义
            functions = []
            function_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)(?:\s*:\s*[^{]+)?\s*\{'
            for match in re.finditer(function_pattern, source_code):
                function_name = match.group(1)
                
                # 提取修饰符
                modifiers = []
                if 'export' in match.group(0):
                    modifiers.append('export')
                if 'async' in match.group(0):
                    modifiers.append('async')
                
                function_info = TypeScriptFunctionInfo(
                    name=function_name,
                    line_number=1,
                    end_line=1,
                    modifiers=modifiers,
                    is_async='async' in modifiers,
                    is_export='export' in modifiers
                )
                functions.append(function_info)
            
            # 提取类型定义
            types = []
            type_pattern = r'(?:export\s+)?type\s+(\w+)\s*=\s*([^;]+);'
            for match in re.finditer(type_pattern, source_code):
                type_name = match.group(1)
                type_definition = match.group(2).strip()
                
                # 提取修饰符
                modifiers = []
                if 'export' in match.group(0):
                    modifiers.append('export')
                
                type_info = TypeScriptTypeInfo(
                    name=type_name,
                    line_number=1,
                    end_line=1,
                    type_definition=type_definition,
                    modifiers=modifiers,
                    is_export='export' in modifiers
                )
                types.append(type_info)
            
            # 提取枚举定义
            enums = []
            enum_pattern = r'(?:export\s+)?enum\s+(\w+)\s*\{'
            for match in re.finditer(enum_pattern, source_code):
                enum_name = match.group(1)
                
                # 提取修饰符
                modifiers = []
                if 'export' in match.group(0):
                    modifiers.append('export')
                
                enum_info = TypeScriptEnumInfo(
                    name=enum_name,
                    line_number=1,
                    end_line=len(lines),
                    modifiers=modifiers,
                    is_export='export' in modifiers
                )
                
                # 提取枚举成员
                self._extract_enum_members(source_code, enum_info)
                enums.append(enum_info)
            
            # 使用正确的文件名
            module_name = Path(file_path).stem if file_path != "<string>" else "Unknown"
            
            return TypeScriptModuleInfo(
                name=module_name,
                file_path=file_path,
                imports=imports,
                exports=exports,
                interfaces=interfaces,
                classes=classes,
                functions=functions,
                types=types,
                enums=enums,
                line_count=len(lines),
                language=LanguageEnum.TYPESCRIPT
            )
            
        except Exception as e:
            logger.error(f"正则表达式解析失败: {e}")
            return None
    
    def _extract_interface_members(self, source_code: str, interface_info: TypeScriptInterfaceInfo):
        """提取接口中的属性和方法"""
        # 提取属性
        property_pattern = r'(?:readonly\s+)?(\w+)(?:\?)?\s*:\s*([^;]+);'
        for match in re.finditer(property_pattern, source_code):
            property_name = match.group(1)
            property_type = match.group(2).strip()
            
            # 提取修饰符
            modifiers = []
            if 'readonly' in match.group(0):
                modifiers.append('readonly')
            if '?' in match.group(0):
                modifiers.append('optional')
            
            property_info = TypeScriptPropertyInfo(
                name=property_name,
                line_number=1,
                end_line=1,
                property_type=property_type,
                modifiers=modifiers,
                is_readonly='readonly' in modifiers,
                is_optional='optional' in modifiers
            )
            interface_info.properties.append(property_info)
        
        # 提取方法
        method_pattern = r'(\w+)\s*\([^)]*\)(?:\s*:\s*[^{]+)?\s*(?:\{|;)'
        for match in re.finditer(method_pattern, source_code):
            method_name = match.group(1)
            
            method_info = TypeScriptFunctionInfo(
                name=method_name,
                line_number=1,
                end_line=1,
                is_method=True
            )
            interface_info.methods.append(method_info)
    
    def _extract_class_members(self, source_code: str, class_info: TypeScriptClassInfo):
        """提取类中的属性和方法"""
        # 提取属性
        property_pattern = r'(?:public|private|protected|readonly|static)?\s*(?:public|private|protected|readonly|static)?\s*(\w+)(?:\?)?\s*:\s*([^;]+)(?:\s*=\s*[^;]+)?;'
        for match in re.finditer(property_pattern, source_code):
            property_name = match.group(1)
            property_type = match.group(2).strip()
            
            # 提取修饰符
            modifiers = []
            property_text = match.group(0)
            if 'public' in property_text:
                modifiers.append('public')
            elif 'private' in property_text:
                modifiers.append('private')
            elif 'protected' in property_text:
                modifiers.append('protected')
            if 'readonly' in property_text:
                modifiers.append('readonly')
            if 'static' in property_text:
                modifiers.append('static')
            if '?' in property_text:
                modifiers.append('optional')
            
            property_info = TypeScriptPropertyInfo(
                name=property_name,
                line_number=1,
                end_line=1,
                property_type=property_type,
                modifiers=modifiers,
                is_public='public' in modifiers,
                is_private='private' in modifiers,
                is_protected='protected' in modifiers,
                is_readonly='readonly' in modifiers,
                is_static='static' in modifiers,
                is_optional='optional' in modifiers
            )
            class_info.properties.append(property_info)
        
        # 提取方法
        method_pattern = r'(?:public|private|protected|static|async|abstract)?\s*(?:public|private|protected|static|async|abstract)?\s*(?:public|private|protected|static|async|abstract)?\s*(\w+)\s*\([^)]*\)(?:\s*:\s*[^{]+)?\s*\{'
        for match in re.finditer(method_pattern, source_code):
            method_name = match.group(1)
            
            # 检查是否为构造函数
            is_constructor = method_name == 'constructor'
            
            # 提取修饰符
            modifiers = []
            method_text = match.group(0)
            if 'public' in method_text:
                modifiers.append('public')
            elif 'private' in method_text:
                modifiers.append('private')
            elif 'protected' in method_text:
                modifiers.append('protected')
            if 'static' in method_text:
                modifiers.append('static')
            if 'async' in method_text:
                modifiers.append('async')
            if 'abstract' in method_text:
                modifiers.append('abstract')
            
            method_info = TypeScriptFunctionInfo(
                name=method_name,
                line_number=1,
                end_line=1,
                modifiers=modifiers,
                is_method=True,
                is_constructor=is_constructor,
                is_public='public' in modifiers,
                is_private='private' in modifiers,
                is_protected='protected' in modifiers,
                is_static='static' in modifiers,
                is_async='async' in modifiers,
                is_abstract='abstract' in modifiers
            )
            
            if is_constructor:
                class_info.constructors.append(method_info)
            else:
                class_info.methods.append(method_info)
    
    def _extract_enum_members(self, source_code: str, enum_info: TypeScriptEnumInfo):
        """提取枚举成员"""
        # 简单的枚举成员提取
        member_pattern = r'(\w+)(?:\s*=\s*[^,}]+)?,?'
        for match in re.finditer(member_pattern, source_code):
            member_name = match.group(1)
            if member_name and member_name not in ['enum', enum_info.name]:
                enum_info.members.append(member_name)
    
    def parse_directory(self, directory: str, 
                       exclude_patterns: Optional[List[str]] = None) -> Dict[str, TypeScriptModuleInfo]:
        """
        解析目录中的所有TypeScript文件
        
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
            for file_path in Path(directory).rglob("*.ts"):
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
            
            # 也解析 .tsx 文件
            for file_path in Path(directory).rglob("*.tsx"):
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


class TypeScriptASTVisitor:
    """
    TypeScript AST访问者
    
    遍历tree-sitter AST树，提取代码结构信息。
    """
    
    def __init__(self):
        """初始化访问者"""
        self.module_docstring: Optional[str] = None
        self.imports: List[str] = []
        self.exports: List[str] = []
        self.interfaces: List[TypeScriptInterfaceInfo] = []
        self.classes: List[TypeScriptClassInfo] = []
        self.functions: List[TypeScriptFunctionInfo] = []
        self.types: List[TypeScriptTypeInfo] = []
        self.enums: List[TypeScriptEnumInfo] = []
        self.variables: List[str] = []
        self.constants: List[str] = []
        self._current_class: Optional[TypeScriptClassInfo] = None
        self._current_interface: Optional[TypeScriptInterfaceInfo] = None
    
    def visit(self, node: Node):
        """访问节点"""
        if node.type == 'import_statement':
            self._visit_import_statement(node)
        elif node.type == 'export_statement':
            self._visit_export_statement(node)
        elif node.type == 'interface_declaration':
            self._visit_interface_declaration(node)
        elif node.type == 'class_declaration':
            self._visit_class_declaration(node)
        elif node.type == 'function_declaration':
            self._visit_function_declaration(node)
        elif node.type == 'type_alias_declaration':
            self._visit_type_alias_declaration(node)
        elif node.type == 'enum_declaration':
            self._visit_enum_declaration(node)
        elif node.type == 'variable_declaration':
            self._visit_variable_declaration(node)
        
        # 递归访问子节点
        for child in node.children:
            self.visit(child)
    
    def _visit_import_statement(self, node: Node):
        """访问导入语句"""
        import_text = node.text.decode('utf8').strip()
        # 简单的导入提取
        if 'from' in import_text:
            parts = import_text.split('from')
            if len(parts) >= 2:
                module = parts[1].strip().strip('"\';')
                self.imports.append(module)
    
    def _visit_export_statement(self, node: Node):
        """访问导出语句"""
        export_text = node.text.decode('utf8').strip()
        # 简单的导出提取
        if 'export' in export_text:
            # 提取导出的名称
            for child in node.children:
                if child.type == 'identifier':
                    self.exports.append(child.text.decode('utf8'))
    
    def _visit_interface_declaration(self, node: Node):
        """访问接口声明"""
        interface_info = self._create_interface_info(node)
        self.interfaces.append(interface_info)
        
        # 保存当前接口上下文
        previous_interface = self._current_interface
        self._current_interface = interface_info
        
        # 访问接口体
        for child in node.children:
            if child.type == 'object_type':
                self.visit(child)
        
        # 恢复上下文
        self._current_interface = previous_interface
    
    def _visit_class_declaration(self, node: Node):
        """访问类声明"""
        class_info = self._create_class_info(node)
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
    
    def _visit_function_declaration(self, node: Node):
        """访问函数声明"""
        function_info = self._create_function_info(node)
        
        if self._current_class:
            if function_info.name == 'constructor':
                self._current_class.constructors.append(function_info)
            else:
                self._current_class.methods.append(function_info)
        elif self._current_interface:
            self._current_interface.methods.append(function_info)
        else:
            self.functions.append(function_info)
    
    def _visit_type_alias_declaration(self, node: Node):
        """访问类型别名声明"""
        type_info = self._create_type_info(node)
        self.types.append(type_info)
    
    def _visit_enum_declaration(self, node: Node):
        """访问枚举声明"""
        enum_info = self._create_enum_info(node)
        self.enums.append(enum_info)
    
    def _visit_variable_declaration(self, node: Node):
        """访问变量声明"""
        for child in node.children:
            if child.type == 'identifier':
                var_name = child.text.decode('utf8')
                if var_name.isupper():
                    self.constants.append(var_name)
                else:
                    self.variables.append(var_name)
    
    def _create_interface_info(self, node: Node) -> TypeScriptInterfaceInfo:
        """创建接口信息"""
        interface_info = TypeScriptInterfaceInfo(
            name="",
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1
        )
        
        # 提取接口名
        for child in node.children:
            if child.type == 'identifier':
                interface_info.name = child.text.decode('utf8')
                break
        
        # 提取修饰符
        interface_info.modifiers = self._extract_modifiers(node)
        interface_info.is_export = 'export' in interface_info.modifiers
        
        # 提取继承
        for child in node.children:
            if child.type == 'extends_clause':
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        interface_info.extends.append(grandchild.text.decode('utf8'))
        
        return interface_info
    
    def _create_class_info(self, node: Node) -> TypeScriptClassInfo:
        """创建类信息"""
        class_info = TypeScriptClassInfo(
            name="",
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1
        )
        
        # 提取类名
        for child in node.children:
            if child.type == 'identifier':
                class_info.name = child.text.decode('utf8')
                break
        
        # 提取修饰符
        class_info.modifiers = self._extract_modifiers(node)
        class_info.is_export = 'export' in class_info.modifiers
        class_info.is_abstract = 'abstract' in class_info.modifiers
        
        # 提取继承和实现
        for child in node.children:
            if child.type == 'extends_clause':
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        class_info.extends = grandchild.text.decode('utf8')
            elif child.type == 'implements_clause':
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        class_info.implements.append(grandchild.text.decode('utf8'))
        
        return class_info
    
    def _create_function_info(self, node: Node) -> TypeScriptFunctionInfo:
        """创建函数信息"""
        function_info = TypeScriptFunctionInfo(
            name="",
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1
        )
        
        # 提取函数名
        for child in node.children:
            if child.type == 'identifier':
                function_info.name = child.text.decode('utf8')
                break
        
        # 提取修饰符
        function_info.modifiers = self._extract_modifiers(node)
        function_info.is_export = 'export' in function_info.modifiers
        function_info.is_async = 'async' in function_info.modifiers
        function_info.is_abstract = 'abstract' in function_info.modifiers
        function_info.is_static = 'static' in function_info.modifiers
        function_info.is_public = 'public' in function_info.modifiers
        function_info.is_private = 'private' in function_info.modifiers
        function_info.is_protected = 'protected' in function_info.modifiers
        
        return function_info
    
    def _create_type_info(self, node: Node) -> TypeScriptTypeInfo:
        """创建类型信息"""
        type_info = TypeScriptTypeInfo(
            name="",
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            type_definition=""
        )
        
        # 提取类型名和定义
        for child in node.children:
            if child.type == 'identifier':
                type_info.name = child.text.decode('utf8')
            elif child.type == 'type':
                type_info.type_definition = child.text.decode('utf8')
        
        # 提取修饰符
        type_info.modifiers = self._extract_modifiers(node)
        type_info.is_export = 'export' in type_info.modifiers
        
        return type_info
    
    def _create_enum_info(self, node: Node) -> TypeScriptEnumInfo:
        """创建枚举信息"""
        enum_info = TypeScriptEnumInfo(
            name="",
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1
        )
        
        # 提取枚举名
        for child in node.children:
            if child.type == 'identifier':
                enum_info.name = child.text.decode('utf8')
                break
        
        # 提取修饰符
        enum_info.modifiers = self._extract_modifiers(node)
        enum_info.is_export = 'export' in enum_info.modifiers
        
        # 提取枚举成员
        for child in node.children:
            if child.type == 'enum_body':
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        enum_info.members.append(grandchild.text.decode('utf8'))
        
        return enum_info
    
    def _extract_modifiers(self, node: Node) -> List[str]:
        """提取修饰符"""
        modifiers = []
        for child in node.children:
            if child.type in ['export', 'abstract', 'async', 'static', 'public', 'private', 'protected', 'readonly']:
                modifiers.append(child.type)
        return modifiers


# 便捷函数
def parse_typescript_file(file_path: str) -> Optional[TypeScriptModuleInfo]:
    """
    解析TypeScript文件（便捷函数）
    
    Args:
        file_path: 文件路径
        
    Returns:
        模块信息
    """
    parser = TypeScriptASTParser()
    return parser.parse_file(file_path)


def parse_typescript_source(source_code: str, file_path: str = "<string>") -> Optional[TypeScriptModuleInfo]:
    """
    解析TypeScript源代码（便捷函数）
    
    Args:
        source_code: 源代码字符串
        file_path: 文件路径
        
    Returns:
        模块信息
    """
    parser = TypeScriptASTParser()
    return parser.parse_source(source_code, file_path)


def parse_typescript_directory(directory: str, 
                              exclude_patterns: Optional[List[str]] = None) -> Dict[str, TypeScriptModuleInfo]:
    """
    解析目录中的所有TypeScript文件（便捷函数）
    
    Args:
        directory: 目录路径
        exclude_patterns: 排除的文件模式列表
        
    Returns:
        文件路径到模块信息的映射
    """
    parser = TypeScriptASTParser()
    return parser.parse_directory(directory, exclude_patterns) 