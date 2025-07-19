"""
Go代码AST解析器

使用tree-sitter库解析Go代码，提取包、函数、结构体等信息。
"""

import tree_sitter
from tree_sitter import Language, Parser
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging

from .language_detector import Language as LangType, detect_language
from .ast_cache import get_global_cache

logger = logging.getLogger(__name__)


@dataclass
class GoFunctionInfo:
    """Go函数信息"""
    name: str
    line_number: int
    end_line: int
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    return_types: List[str] = field(default_factory=list)
    receiver: Optional[str] = None
    is_method: bool = False
    is_exported: bool = False


@dataclass
class GoStructInfo:
    """Go结构体信息"""
    name: str
    line_number: int
    end_line: int
    docstring: Optional[str] = None
    fields: List[str] = field(default_factory=list)
    methods: List[GoFunctionInfo] = field(default_factory=list)
    is_exported: bool = False


@dataclass
class GoInterfaceInfo:
    """Go接口信息"""
    name: str
    line_number: int
    end_line: int
    docstring: Optional[str] = None
    methods: List[str] = field(default_factory=list)
    is_exported: bool = False


@dataclass
class GoModuleInfo:
    """Go模块信息"""
    name: str
    file_path: str
    package_name: str
    docstring: Optional[str] = None
    imports: List[str] = field(default_factory=list)
    functions: List[GoFunctionInfo] = field(default_factory=list)
    structs: List[GoStructInfo] = field(default_factory=list)
    interfaces: List[GoInterfaceInfo] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    constants: List[str] = field(default_factory=list)
    line_count: int = 0
    language: LangType = LangType.GO


class GoASTParser:
    """
    Go代码AST解析器
    
    使用tree-sitter库解析Go代码，提取详细的代码结构信息。
    """
    
    def __init__(self, use_cache: bool = True):
        """
        初始化Go AST解析器
        
        Args:
            use_cache: 是否使用缓存
        """
        self.parser = None
        self.use_cache = use_cache
        self.cache = get_global_cache() if use_cache else None
        self._init_parser()
    
    def _init_parser(self):
        """初始化tree-sitter解析器"""
        try:
            # 尝试加载Go语言库
            Language.build_library(
                'build/my-languages.so',
                [
                    'vendor/tree-sitter-go'
                ]
            )
            go_lang = Language('build/my-languages.so', 'go')
            self.parser = Parser()
            self.parser.set_language(go_lang)
        except Exception as e:
            logger.warning(f"无法初始化Go tree-sitter解析器: {e}")
            logger.info("将使用备用解析方法")
            self.parser = None
    
    def parse_file(self, file_path: str) -> Optional[GoModuleInfo]:
        """
        解析Go文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            模块信息，如果解析失败则返回None
        """
        try:
            # 检查文件语言
            language = detect_language(file_path)
            if language != LangType.GO:
                logger.warning(f"文件 {file_path} 不是Go文件")
                return None
            
            # 尝试从缓存获取
            if self.use_cache and self.cache:
                cached_result = self.cache.get(file_path)
                if cached_result is not None:
                    logger.debug(f"从缓存获取Go AST解析结果: {file_path}")
                    return cached_result
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # 解析AST
            module_info = self.parse_source(source_code, file_path)
            
            # 缓存结果
            if self.use_cache and self.cache and module_info:
                self.cache.set(file_path, module_info)
                logger.debug(f"缓存Go AST解析结果: {file_path}")
            
            return module_info
            
        except Exception as e:
            logger.error(f"解析文件 {file_path} 时出错: {e}")
            return None
    
    def parse_source(self, source_code: str, file_path: str = "<string>") -> Optional[GoModuleInfo]:
        """
        解析Go源代码
        
        Args:
            source_code: 源代码字符串
            file_path: 文件路径（用于标识）
            
        Returns:
            模块信息，如果解析失败则返回None
        """
        try:
            if self.parser is None:
                # 使用备用解析方法
                return self._parse_with_regex(source_code, file_path)
            
            # 使用tree-sitter解析
            tree = self.parser.parse(bytes(source_code, 'utf8'))
            root_node = tree.root_node
            
            # 创建访问者
            visitor = GoASTVisitor()
            
            # 访问AST
            visitor.visit(root_node)
            
            # 构建模块信息
            module_info = GoModuleInfo(
                name=Path(file_path).stem,
                file_path=file_path,
                package_name=visitor.package_name,
                docstring=visitor.package_docstring,
                imports=visitor.imports,
                functions=visitor.functions,
                structs=visitor.structs,
                interfaces=visitor.interfaces,
                variables=visitor.variables,
                constants=visitor.constants,
                line_count=len(source_code.splitlines()),
                language=LangType.GO
            )
            
            return module_info
            
        except Exception as e:
            logger.error(f"解析Go源代码时出错: {e}")
            return None
    
    def _parse_with_regex(self, source_code: str, file_path: str) -> Optional[GoModuleInfo]:
        """
        使用正则表达式作为备用的Go代码解析方法
        
        Args:
            source_code: 源代码字符串
            file_path: 文件路径
            
        Returns:
            模块信息
        """
        import re
        
        lines = source_code.splitlines()
        package_name = ""
        imports = []
        functions = []
        structs = []
        interfaces = []
        variables = []
        constants = []
        
        # 解析包名
        package_match = re.search(r'^package\s+(\w+)', source_code, re.MULTILINE)
        if package_match:
            package_name = package_match.group(1)
        
        # 解析导入
        import_pattern = r'import\s+(?:\()?([^)]+)(?:\))?'
        import_matches = re.finditer(import_pattern, source_code, re.MULTILINE)
        for match in import_matches:
            import_content = match.group(1)
            # 提取导入路径
            import_paths = re.findall(r'["\']([^"\']+)["\']', import_content)
            imports.extend(import_paths)
        
        # 解析结构体 - 改进版本
        struct_pattern = r'(?://\s*([^\n]*)\s*\n)?\s*type\s+(\w+)\s+struct\s*{'
        struct_matches = re.finditer(struct_pattern, source_code, re.MULTILINE)
        for match in struct_matches:
            docstring = match.group(1)
            struct_name = match.group(2)
            line_num = source_code[:match.start()].count('\n') + 1
            
            struct_info = GoStructInfo(
                name=struct_name,
                line_number=line_num,
                end_line=line_num,
                docstring=docstring.strip() if docstring else None,
                is_exported=struct_name[0].isupper() if struct_name else False
            )
            structs.append(struct_info)
        
        # 解析函数 - 改进版本
        func_pattern = r'(?://\s*([^\n]*)\s*\n)?\s*func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(([^)]*)\)\s*(?:([^{]+))?{'
        func_matches = re.finditer(func_pattern, source_code, re.MULTILINE)
        for match in func_matches:
            docstring = match.group(1)
            func_name = match.group(2)
            params_str = match.group(3)
            return_type_str = match.group(4)
            
            line_num = source_code[:match.start()].count('\n') + 1
            
            # 解析参数
            parameters = []
            if params_str:
                # 简单的参数解析
                param_parts = [p.strip() for p in params_str.split(',') if p.strip()]
                for param in param_parts:
                    if ' ' in param:
                        param_name = param.split()[0]
                        parameters.append(param_name)
            
            # 解析返回类型
            return_types = []
            if return_type_str:
                return_type_str = return_type_str.strip()
                if return_type_str:
                    return_types.append(return_type_str)
            
            # 检查是否为方法
            is_method = False
            receiver = None
            method_match = re.search(r'func\s+\(([^)]+)\)\s+' + re.escape(func_name), match.group(0))
            if method_match:
                is_method = True
                receiver = method_match.group(1)
            
            func_info = GoFunctionInfo(
                name=func_name,
                line_number=line_num,
                end_line=line_num,
                docstring=docstring.strip() if docstring else None,
                parameters=parameters,
                return_types=return_types,
                receiver=receiver,
                is_method=is_method,
                is_exported=func_name[0].isupper() if func_name else False
            )
            
            # 如果是方法，尝试关联到结构体
            if is_method and receiver:
                # 从接收者中提取类型名
                receiver_type = receiver.split()[-1]  # 取最后一个部分作为类型
                if receiver_type.startswith('*'):
                    receiver_type = receiver_type[1:]  # 移除指针符号
                
                # 查找对应的结构体
                for struct in structs:
                    if struct.name == receiver_type:
                        struct.methods.append(func_info)
                        break
                else:
                    # 如果没有找到对应的结构体，作为普通函数处理
                    functions.append(func_info)
            else:
                functions.append(func_info)
        
        # 解析接口 - 改进版本
        interface_pattern = r'(?://\s*([^\n]*)\s*\n)?\s*type\s+(\w+)\s+interface\s*{'
        interface_matches = re.finditer(interface_pattern, source_code, re.MULTILINE)
        for match in interface_matches:
            docstring = match.group(1)
            interface_name = match.group(2)
            line_num = source_code[:match.start()].count('\n') + 1
            
            interfaces.append(GoInterfaceInfo(
                name=interface_name,
                line_number=line_num,
                end_line=line_num,
                docstring=docstring.strip() if docstring else None,
                is_exported=interface_name[0].isupper() if interface_name else False
            ))
        
        # 改进的变量和常量解析
        # 解析常量块
        const_block_pattern = r'const\s*\(([^)]+)\)'
        const_block_matches = re.finditer(const_block_pattern, source_code, re.MULTILINE | re.DOTALL)
        for match in const_block_matches:
            const_block = match.group(1)
            # 提取常量名
            const_names = re.findall(r'(\w+)\s*=', const_block)
            constants.extend(const_names)
        
        # 解析变量块
        var_block_pattern = r'var\s*\(([^)]+)\)'
        var_block_matches = re.finditer(var_block_pattern, source_code, re.MULTILINE | re.DOTALL)
        for match in var_block_matches:
            var_block = match.group(1)
            # 提取变量名
            var_names = re.findall(r'(\w+)\s*=', var_block)
            for var_name in var_names:
                if var_name.isupper():
                    constants.append(var_name)
                else:
                    variables.append(var_name)
        
        return GoModuleInfo(
            name=Path(file_path).stem,
            file_path=file_path,
            package_name=package_name,
            imports=imports,
            functions=functions,
            structs=structs,
            interfaces=interfaces,
            variables=variables,
            constants=constants,
            line_count=len(lines),
            language=LangType.GO
        )
    
    def parse_directory(self, directory: str, 
                       exclude_patterns: Optional[List[str]] = None) -> Dict[str, GoModuleInfo]:
        """
        解析目录中的所有Go文件
        
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
            for file_path in Path(directory).rglob("*.go"):
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


class GoASTVisitor:
    """
    Go AST访问者
    
    遍历tree-sitter AST树，提取代码结构信息。
    """
    
    def __init__(self):
        """初始化访问者"""
        self.package_name: str = ""
        self.package_docstring: Optional[str] = None
        self.imports: List[str] = []
        self.functions: List[GoFunctionInfo] = []
        self.structs: List[GoStructInfo] = []
        self.interfaces: List[GoInterfaceInfo] = []
        self.variables: List[str] = []
        self.constants: List[str] = []
        self._current_struct: Optional[GoStructInfo] = None
    
    def visit(self, node: tree_sitter.Node):
        """访问AST节点"""
        if node.type == 'package_clause':
            self._visit_package_clause(node)
        elif node.type == 'import_declaration':
            self._visit_import_declaration(node)
        elif node.type == 'function_declaration':
            self._visit_function_declaration(node)
        elif node.type == 'type_declaration':
            self._visit_type_declaration(node)
        elif node.type == 'var_declaration':
            self._visit_var_declaration(node)
        elif node.type == 'const_declaration':
            self._visit_const_declaration(node)
        
        # 递归访问子节点
        for child in node.children:
            self.visit(child)
    
    def _visit_package_clause(self, node: tree_sitter.Node):
        """访问包声明"""
        for child in node.children:
            if child.type == 'package_identifier':
                self.package_name = child.text.decode('utf8')
            elif child.type == 'comment':
                self.package_docstring = child.text.decode('utf8').strip()
    
    def _visit_import_declaration(self, node: tree_sitter.Node):
        """访问导入声明"""
        for child in node.children:
            if child.type == 'import_spec_list':
                for spec in child.children:
                    if spec.type == 'import_spec':
                        import_path = spec.text.decode('utf8').strip('"\'')
                        self.imports.append(import_path)
    
    def _visit_function_declaration(self, node: tree_sitter.Node):
        """访问函数声明"""
        func_info = GoFunctionInfo(
            name="",
            line_number=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1
        )
        
        for child in node.children:
            if child.type == 'identifier':
                func_info.name = child.text.decode('utf8')
                func_info.is_exported = func_info.name[0].isupper() if func_info.name else False
            elif child.type == 'receiver':
                func_info.is_method = True
                # 提取接收者类型
                receiver_text = child.text.decode('utf8')
                func_info.receiver = receiver_text.strip('()')
            elif child.type == 'parameter_list':
                # 提取参数
                params = self._extract_parameters(child)
                func_info.parameters = params
            elif child.type == 'result':
                # 提取返回类型
                return_types = self._extract_return_types(child)
                func_info.return_types = return_types
            elif child.type == 'comment':
                func_info.docstring = child.text.decode('utf8').strip()
        
        if func_info.name:
            if self._current_struct:
                self._current_struct.methods.append(func_info)
            else:
                self.functions.append(func_info)
    
    def _visit_type_declaration(self, node: tree_sitter.Node):
        """访问类型声明"""
        for child in node.children:
            if child.type == 'type_spec':
                type_name = ""
                for grandchild in child.children:
                    if grandchild.type == 'type_identifier':
                        type_name = grandchild.text.decode('utf8')
                        break
                
                if type_name:
                    is_exported = type_name[0].isupper() if type_name else False
                    
                    # 检查是否为结构体
                    if 'struct' in child.text.decode('utf8'):
                        struct_info = GoStructInfo(
                            name=type_name,
                            line_number=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                            is_exported=is_exported
                        )
                        self.structs.append(struct_info)
                        self._current_struct = struct_info
                    
                    # 检查是否为接口
                    elif 'interface' in child.text.decode('utf8'):
                        interface_info = GoInterfaceInfo(
                            name=type_name,
                            line_number=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                            is_exported=is_exported
                        )
                        self.interfaces.append(interface_info)
    
    def _visit_var_declaration(self, node: tree_sitter.Node):
        """访问变量声明"""
        for child in node.children:
            if child.type == 'var_spec':
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        var_name = grandchild.text.decode('utf8')
                        if var_name.isupper():
                            self.constants.append(var_name)
                        else:
                            self.variables.append(var_name)
    
    def _visit_const_declaration(self, node: tree_sitter.Node):
        """访问常量声明"""
        for child in node.children:
            if child.type == 'const_spec':
                for grandchild in child.children:
                    if grandchild.type == 'identifier':
                        const_name = grandchild.text.decode('utf8')
                        self.constants.append(const_name)
    
    def _extract_parameters(self, param_list: tree_sitter.Node) -> List[str]:
        """提取函数参数"""
        params = []
        for child in param_list.children:
            if child.type == 'parameter_declaration':
                param_text = child.text.decode('utf8')
                # 简单的参数提取
                if ' ' in param_text:
                    param_name = param_text.split()[0]
                    params.append(param_name)
        return params
    
    def _extract_return_types(self, result: tree_sitter.Node) -> List[str]:
        """提取返回类型"""
        types = []
        for child in result.children:
            if child.type == 'type':
                type_text = child.text.decode('utf8')
                types.append(type_text)
        return types


# 便捷函数
def parse_go_file(file_path: str, use_cache: bool = True) -> Optional[GoModuleInfo]:
    """
    解析Go文件（便捷函数）
    
    Args:
        file_path: 文件路径
        use_cache: 是否使用缓存
        
    Returns:
        模块信息
    """
    parser = GoASTParser(use_cache=use_cache)
    return parser.parse_file(file_path)


def parse_go_source(source_code: str, file_path: str = "<string>", use_cache: bool = True) -> Optional[GoModuleInfo]:
    """
    解析Go源代码（便捷函数）
    
    Args:
        source_code: 源代码字符串
        file_path: 文件路径
        use_cache: 是否使用缓存
        
    Returns:
        模块信息
    """
    parser = GoASTParser(use_cache=use_cache)
    return parser.parse_source(source_code, file_path)


def parse_go_directory(directory: str, 
                      exclude_patterns: Optional[List[str]] = None,
                      use_cache: bool = True) -> Dict[str, GoModuleInfo]:
    """
    解析目录中的所有Go文件（便捷函数）
    
    Args:
        directory: 目录路径
        exclude_patterns: 排除的文件模式列表
        use_cache: 是否使用缓存
        
    Returns:
        文件路径到模块信息的映射
    """
    parser = GoASTParser(use_cache=use_cache)
    return parser.parse_directory(directory, exclude_patterns) 