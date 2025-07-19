"""
模块映射生成功能

统一管理不同编程语言的模块信息，提供跨语言的模块映射和分析功能。
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, field
import logging
from collections import defaultdict

from .language_detector import Language, detect_language
from .ast_parser import ModuleInfo as PythonModuleInfo
from .go_ast_parser import GoModuleInfo
from .java_ast_parser import JavaModuleInfo
from .typescript_ast_parser import TypeScriptModuleInfo

logger = logging.getLogger(__name__)


@dataclass
class ModuleMapping:
    """模块映射信息"""
    file_path: str
    module_name: str
    language: Language
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    line_count: int = 0
    complexity_score: float = 0.0
    last_modified: Optional[float] = None


@dataclass
class ProjectMapping:
    """项目映射信息"""
    project_path: str
    modules: Dict[str, ModuleMapping] = field(default_factory=dict)
    language_stats: Dict[Language, int] = field(default_factory=dict)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    circular_dependencies: List[List[str]] = field(default_factory=list)
    unused_modules: List[str] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0


class ModuleMapper:
    """
    模块映射生成器
    
    统一管理不同编程语言的模块信息，提供跨语言的模块映射和分析功能。
    """
    
    def __init__(self):
        """初始化模块映射器"""
        self.language_parsers = {
            Language.PYTHON: self._parse_python_module,
            Language.GO: self._parse_go_module,
            Language.JAVA: self._parse_java_module,
            Language.TYPESCRIPT: self._parse_typescript_module,
        }
    
    def generate_project_mapping(self, project_path: str, 
                                exclude_patterns: Optional[List[str]] = None) -> ProjectMapping:
        """
        生成项目映射
        
        Args:
            project_path: 项目根目录路径
            exclude_patterns: 排除的文件模式列表
            
        Returns:
            项目映射信息
        """
        if exclude_patterns is None:
            exclude_patterns = []
        
        project_mapping = ProjectMapping(project_path=project_path)
        
        try:
            # 扫描项目中的所有文件
            all_files = self._scan_project_files(project_path, exclude_patterns)
            
            # 解析每个文件
            for file_path in all_files:
                try:
                    module_mapping = self._parse_file_to_mapping(file_path)
                    if module_mapping:
                        project_mapping.modules[file_path] = module_mapping
                        project_mapping.total_files += 1
                        project_mapping.total_lines += module_mapping.line_count
                        
                        # 更新语言统计
                        lang = module_mapping.language
                        project_mapping.language_stats[lang] = project_mapping.language_stats.get(lang, 0) + 1
                        
                except Exception as e:
                    logger.warning(f"解析文件 {file_path} 时出错: {e}")
                    continue
            
            # 构建依赖图
            self._build_dependency_graph(project_mapping)
            
            # 分析依赖关系
            self._analyze_dependencies(project_mapping)
            
            return project_mapping
            
        except Exception as e:
            logger.error(f"生成项目映射时出错: {e}")
            return project_mapping
    
    def _scan_project_files(self, project_path: str, exclude_patterns: List[str]) -> List[str]:
        """扫描项目文件"""
        files = []
        project_path_obj = Path(project_path)
        
        # 支持的文件扩展名
        supported_extensions = {
            '.py', '.pyw', '.pyx', '.pyi',  # Python
            '.go',  # Go
            '.java',  # Java
            '.ts', '.tsx',  # TypeScript
        }
        
        try:
            for file_path in project_path_obj.rglob("*"):
                if not file_path.is_file():
                    continue
                
                # 排除隐藏目录
                if any(part.startswith('.') for part in file_path.parts):
                    continue
                
                # 检查文件扩展名
                if file_path.suffix.lower() not in supported_extensions:
                    continue
                
                file_path_str = str(file_path)
                
                # 检查排除模式
                if any(pattern in file_path_str for pattern in exclude_patterns):
                    continue
                
                files.append(file_path_str)
                
        except Exception as e:
            logger.error(f"扫描项目文件时出错: {e}")
        
        return files
    
    def _parse_file_to_mapping(self, file_path: str) -> Optional[ModuleMapping]:
        """解析文件为模块映射"""
        try:
            # 检测语言
            language = detect_language(file_path)
            
            # 获取对应的解析器
            parser_func = self.language_parsers.get(language)
            if not parser_func:
                logger.warning(f"不支持的语言: {language} for {file_path}")
                return None
            
            # 解析模块
            module_info = parser_func(file_path)
            if not module_info:
                return None
            
            # 转换为模块映射
            return self._convert_to_module_mapping(module_info, file_path, language)
            
        except Exception as e:
            logger.error(f"解析文件 {file_path} 为模块映射时出错: {e}")
            return None
    
    def _parse_python_module(self, file_path: str) -> Optional[PythonModuleInfo]:
        """解析Python模块"""
        from .ast_parser import parse_python_file
        return parse_python_file(file_path)
    
    def _parse_go_module(self, file_path: str) -> Optional[GoModuleInfo]:
        """解析Go模块"""
        from .go_ast_parser import parse_go_file
        return parse_go_file(file_path)
    
    def _parse_java_module(self, file_path: str) -> Optional[JavaModuleInfo]:
        """解析Java模块"""
        from .java_ast_parser import parse_java_file
        return parse_java_file(file_path)
    
    def _parse_typescript_module(self, file_path: str) -> Optional[TypeScriptModuleInfo]:
        """解析TypeScript模块"""
        from .typescript_ast_parser import parse_typescript_file
        return parse_typescript_file(file_path)
    
    def _convert_to_module_mapping(self, module_info: Any, file_path: str, language: Language) -> ModuleMapping:
        """转换模块信息为模块映射"""
        # 获取文件修改时间
        last_modified = os.path.getmtime(file_path) if os.path.exists(file_path) else None
        
        # 计算复杂度分数
        complexity_score = self._calculate_complexity_score(module_info)
        
        # 提取依赖信息
        dependencies = self._extract_dependencies(module_info, language)
        exports = self._extract_exports(module_info, language)
        imports = self._extract_imports(module_info, language)
        
        return ModuleMapping(
            file_path=file_path,
            module_name=module_info.name,
            language=language,
            dependencies=dependencies,
            exports=exports,
            imports=imports,
            line_count=module_info.line_count,
            complexity_score=complexity_score,
            last_modified=last_modified
        )
    
    def _calculate_complexity_score(self, module_info: Any) -> float:
        """计算模块复杂度分数"""
        score = 0.0
        
        # 基础分数：行数
        score += module_info.line_count * 0.1
        
        # 函数数量
        if hasattr(module_info, 'functions'):
            score += len(module_info.functions) * 2.0
        
        # 类数量
        if hasattr(module_info, 'classes'):
            score += len(module_info.classes) * 3.0
        
        # 方法数量（在类中）
        if hasattr(module_info, 'classes'):
            for class_info in module_info.classes:
                if hasattr(class_info, 'methods'):
                    score += len(class_info.methods) * 1.5
        
        # 导入数量
        if hasattr(module_info, 'imports'):
            score += len(module_info.imports) * 0.5
        
        # 导出数量
        if hasattr(module_info, 'exports'):
            score += len(module_info.exports) * 0.3
        
        return round(score, 2)
    
    def _extract_dependencies(self, module_info: Any, language: Language) -> List[str]:
        """提取依赖信息"""
        dependencies = []
        
        if language == Language.PYTHON:
            # Python: 从imports和from_imports提取
            if hasattr(module_info, 'imports'):
                dependencies.extend(module_info.imports)
            if hasattr(module_info, 'from_imports'):
                dependencies.extend(module_info.from_imports)
        
        elif language == Language.GO:
            # Go: 从imports提取
            if hasattr(module_info, 'imports'):
                dependencies.extend(module_info.imports)
        
        elif language == Language.JAVA:
            # Java: 从imports提取
            if hasattr(module_info, 'imports'):
                dependencies.extend(module_info.imports)
        
        elif language == Language.TYPESCRIPT:
            # TypeScript: 从imports提取
            if hasattr(module_info, 'imports'):
                dependencies.extend(module_info.imports)
        
        return dependencies
    
    def _extract_exports(self, module_info: Any, language: Language) -> List[str]:
        """提取导出信息"""
        exports = []
        
        if language == Language.PYTHON:
            # Python: 通常没有显式的export，但可以从函数和类名推断
            if hasattr(module_info, 'functions'):
                for func in module_info.functions:
                    if not func.name.startswith('_'):
                        exports.append(func.name)
            if hasattr(module_info, 'classes'):
                for cls in module_info.classes:
                    if not cls.name.startswith('_'):
                        exports.append(cls.name)
        
        elif language == Language.GO:
            # Go: 从导出的函数、结构体、接口提取
            if hasattr(module_info, 'functions'):
                for func in module_info.functions:
                    if func.is_exported:
                        exports.append(func.name)
            if hasattr(module_info, 'structs'):
                for struct in module_info.structs:
                    if struct.is_exported:
                        exports.append(struct.name)
            if hasattr(module_info, 'interfaces'):
                for interface in module_info.interfaces:
                    if interface.is_exported:
                        exports.append(interface.name)
        
        elif language == Language.JAVA:
            # Java: 从导出的类、接口、枚举提取
            if hasattr(module_info, 'classes'):
                for cls in module_info.classes:
                    if cls.is_export:
                        exports.append(cls.name)
            if hasattr(module_info, 'interfaces'):
                for interface in module_info.interfaces:
                    if interface.is_export:
                        exports.append(interface.name)
            if hasattr(module_info, 'enums'):
                for enum in module_info.enums:
                    if enum.is_export:
                        exports.append(enum.name)
        
        elif language == Language.TYPESCRIPT:
            # TypeScript: 从导出的接口、类、函数、类型、枚举提取
            if hasattr(module_info, 'interfaces'):
                for interface in module_info.interfaces:
                    if interface.is_export:
                        exports.append(interface.name)
            if hasattr(module_info, 'classes'):
                for cls in module_info.classes:
                    if cls.is_export:
                        exports.append(cls.name)
            if hasattr(module_info, 'functions'):
                for func in module_info.functions:
                    if func.is_export:
                        exports.append(func.name)
            if hasattr(module_info, 'types'):
                for type_info in module_info.types:
                    if type_info.is_export:
                        exports.append(type_info.name)
            if hasattr(module_info, 'enums'):
                for enum in module_info.enums:
                    if enum.is_export:
                        exports.append(enum.name)
        
        return exports
    
    def _extract_imports(self, module_info: Any, language: Language) -> List[str]:
        """提取导入信息"""
        imports = []
        
        if hasattr(module_info, 'imports'):
            imports.extend(module_info.imports)
        
        return imports
    
    def _build_dependency_graph(self, project_mapping: ProjectMapping):
        """构建依赖图"""
        # 初始化依赖图
        for file_path, module_mapping in project_mapping.modules.items():
            project_mapping.dependency_graph[file_path] = []
        
        # 构建依赖关系
        for file_path, module_mapping in project_mapping.modules.items():
            for dependency in module_mapping.dependencies:
                # 查找依赖对应的文件
                dependent_file = self._find_dependent_file(dependency, project_mapping)
                if dependent_file:
                    project_mapping.dependency_graph[file_path].append(dependent_file)
                    # 同时更新被依赖文件的dependents
                    if dependent_file in project_mapping.modules:
                        project_mapping.modules[dependent_file].dependents.append(file_path)
    
    def _find_dependent_file(self, dependency: str, project_mapping: ProjectMapping) -> Optional[str]:
        """查找依赖对应的文件"""
        # 简单的依赖解析逻辑
        # 在实际项目中，这需要更复杂的模块解析逻辑
        
        # 检查是否是相对导入
        if dependency.startswith('.'):
            # 相对导入，需要更复杂的解析
            return None
        
        # 检查是否是标准库或第三方库
        if dependency in ['os', 'sys', 'json', 're', 'pathlib', 'typing']:
            return None
        
        # 在项目中查找可能的文件
        for file_path in project_mapping.modules:
            module_name = project_mapping.modules[file_path].module_name
            if module_name == dependency:
                return file_path
        
        return None
    
    def _analyze_dependencies(self, project_mapping: ProjectMapping):
        """分析依赖关系"""
        # 检测循环依赖
        project_mapping.circular_dependencies = self._detect_circular_dependencies(project_mapping.dependency_graph)
        
        # 检测未使用的模块
        project_mapping.unused_modules = self._find_unused_modules(project_mapping)
    
    def _detect_circular_dependencies(self, dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
        """检测循环依赖"""
        circular_deps = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]):
            if node in rec_stack:
                # 找到循环依赖
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                circular_deps.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in dependency_graph.get(node, []):
                dfs(neighbor, path.copy())
            
            rec_stack.remove(node)
            path.pop()
        
        for node in dependency_graph:
            if node not in visited:
                dfs(node, [])
        
        return circular_deps
    
    def _find_unused_modules(self, project_mapping: ProjectMapping) -> List[str]:
        """查找未使用的模块"""
        # 返回没有被其他模块依赖的模块
        return [file_path for file_path in project_mapping.modules 
                if len(project_mapping.modules[file_path].dependents) == 0]
    
    def get_module_statistics(self, project_mapping: ProjectMapping) -> Dict[str, Any]:
        """获取模块统计信息"""
        stats = {
            'total_files': project_mapping.total_files,
            'total_lines': project_mapping.total_lines,
            'language_distribution': {lang.value: count for lang, count in project_mapping.language_stats.items()},
            'average_complexity': 0.0,
            'max_complexity': 0.0,
            'circular_dependencies_count': len(project_mapping.circular_dependencies),
            'unused_modules_count': len(project_mapping.unused_modules),
            'dependency_stats': {
                'max_dependencies': 0,
                'average_dependencies': 0.0,
                'max_dependents': 0,
                'average_dependents': 0.0,
            }
        }
        
        if project_mapping.modules:
            complexities = [m.complexity_score for m in project_mapping.modules.values()]
            stats['average_complexity'] = round(sum(complexities) / len(complexities), 2)
            stats['max_complexity'] = max(complexities)
            
            dependencies = [len(m.dependencies) for m in project_mapping.modules.values()]
            dependents = [len(m.dependents) for m in project_mapping.modules.values()]
            
            stats['dependency_stats']['max_dependencies'] = max(dependencies)
            stats['dependency_stats']['average_dependencies'] = round(sum(dependencies) / len(dependencies), 2)
            stats['dependency_stats']['max_dependents'] = max(dependents)
            stats['dependency_stats']['average_dependents'] = round(sum(dependents) / len(dependents), 2)
        
        return stats
    
    def export_mapping_to_json(self, project_mapping: ProjectMapping) -> Dict[str, Any]:
        """导出映射为JSON格式"""
        return {
            'project_path': str(project_mapping.project_path),
            'total_files': project_mapping.total_files,
            'total_lines': project_mapping.total_lines,
            'language_stats': {lang.value: count for lang, count in project_mapping.language_stats.items()},
            'modules': {
                str(file_path): {
                    'module_name': module.module_name,
                    'language': module.language.value,
                    'dependencies': module.dependencies,
                    'dependents': module.dependents,
                    'exports': module.exports,
                    'imports': module.imports,
                    'line_count': module.line_count,
                    'complexity_score': module.complexity_score,
                    'last_modified': module.last_modified
                }
                for file_path, module in project_mapping.modules.items()
            },
            'dependency_graph': {
                str(file_path): [str(dep) for dep in deps]
                for file_path, deps in project_mapping.dependency_graph.items()
            },
            'circular_dependencies': [
                [str(dep) for dep in cycle]
                for cycle in project_mapping.circular_dependencies
            ],
            'unused_modules': [str(file_path) for file_path in project_mapping.unused_modules],
            'statistics': self.get_module_statistics(project_mapping)
        }


# 便捷函数
def generate_project_mapping(project_path: str, 
                            exclude_patterns: Optional[List[str]] = None) -> ProjectMapping:
    """
    生成项目映射（便捷函数）
    
    Args:
        project_path: 项目根目录路径
        exclude_patterns: 排除的文件模式列表
        
    Returns:
        项目映射信息
    """
    mapper = ModuleMapper()
    return mapper.generate_project_mapping(project_path, exclude_patterns)


def export_mapping_to_json(project_mapping: ProjectMapping) -> Dict[str, Any]:
    """
    导出映射为JSON格式（便捷函数）
    
    Args:
        project_mapping: 项目映射信息
        
    Returns:
        JSON格式的映射数据
    """
    mapper = ModuleMapper()
    return mapper.export_mapping_to_json(project_mapping) 