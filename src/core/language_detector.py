"""
编程语言检测模块

支持检测多种编程语言的文件类型，包括Python、Go、Java、TypeScript等。
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum


class Language(Enum):
    """支持的编程语言枚举"""
    PYTHON = "python"
    GO = "go"
    JAVA = "java"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    RUST = "rust"
    CPP = "cpp"
    C = "c"
    CSHARP = "csharp"
    PHP = "php"
    RUBY = "ruby"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SCALA = "scala"
    UNKNOWN = "unknown"


class LanguageDetector:
    """
    编程语言检测器
    
    通过文件扩展名、文件内容和启发式规则检测编程语言。
    """
    
    def __init__(self):
        """初始化语言检测器"""
        self._file_extensions = self._build_extension_map()
        self._shebang_patterns = self._build_shebang_patterns()
        self._content_patterns = self._build_content_patterns()
        self._config_files = self._build_config_files()
    
    def detect_language(self, file_path: str) -> Language:
        """
        检测文件的语言类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            检测到的语言类型
            
        Raises:
            FileNotFoundError: 文件不存在时抛出
            PermissionError: 文件无读取权限时抛出
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not path.is_file():
            return Language.UNKNOWN
        
        # 1. 检查文件扩展名
        extension = path.suffix.lower()
        if extension in self._file_extensions:
            return self._file_extensions[extension]
        
        # 2. 检查配置文件
        if self._is_config_file(path):
            return self._detect_config_language(path)
        
        # 3. 检查文件内容
        try:
            return self._detect_by_content(path)
        except (PermissionError, UnicodeDecodeError):
            return Language.UNKNOWN
    
    def detect_languages_in_directory(self, directory: str, 
                                    exclude_patterns: Optional[List[str]] = None) -> Dict[Language, List[str]]:
        """
        检测目录中所有文件的语言类型
        
        Args:
            directory: 目录路径
            exclude_patterns: 排除的文件模式列表
            
        Returns:
            按语言分组的文件路径字典
        """
        if exclude_patterns is None:
            exclude_patterns = []
        
        result: Dict[Language, List[str]] = {lang: [] for lang in Language}
        
        try:
            for root, dirs, files in os.walk(directory):
                # 排除隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # 检查排除模式
                    if self._should_exclude(file_path, exclude_patterns):
                        continue
                    
                    try:
                        language = self.detect_language(file_path)
                        result[language].append(file_path)
                    except (FileNotFoundError, PermissionError):
                        continue
        except PermissionError:
            pass
        
        return result
    
    def get_supported_languages(self) -> List[Language]:
        """
        获取支持的语言列表
        
        Returns:
            支持的语言列表
        """
        return [lang for lang in Language if lang != Language.UNKNOWN]
    
    def is_supported_language(self, language: Language) -> bool:
        """
        检查是否为支持的语言
        
        Args:
            language: 语言类型
            
        Returns:
            是否为支持的语言
        """
        return language in self.get_supported_languages()
    
    def _build_extension_map(self) -> Dict[str, Language]:
        """构建文件扩展名到语言的映射"""
        return {
            # Python
            '.py': Language.PYTHON,
            '.pyw': Language.PYTHON,
            '.pyx': Language.PYTHON,
            '.pyi': Language.PYTHON,
            
            # Go
            '.go': Language.GO,
            
            # Java
            '.java': Language.JAVA,
            
            # TypeScript/JavaScript
            '.ts': Language.TYPESCRIPT,
            '.tsx': Language.TYPESCRIPT,
            '.js': Language.JAVASCRIPT,
            '.jsx': Language.JAVASCRIPT,
            '.mjs': Language.JAVASCRIPT,
            
            # Rust
            '.rs': Language.RUST,
            
            # C/C++
            '.cpp': Language.CPP,
            '.cc': Language.CPP,
            '.cxx': Language.CPP,
            '.hpp': Language.CPP,
            '.h': Language.C,
            '.c': Language.C,
            
            # C#
            '.cs': Language.CSHARP,
            
            # PHP
            '.php': Language.PHP,
            
            # Ruby
            '.rb': Language.RUBY,
            
            # Swift
            '.swift': Language.SWIFT,
            
            # Kotlin
            '.kt': Language.KOTLIN,
            '.kts': Language.KOTLIN,
            
            # Scala
            '.scala': Language.SCALA,
        }
    
    def _build_shebang_patterns(self) -> Dict[re.Pattern, Language]:
        """构建shebang模式到语言的映射"""
        return {
            re.compile(r'^#!.*python', re.IGNORECASE): Language.PYTHON,
            re.compile(r'^#!.*go', re.IGNORECASE): Language.GO,
            re.compile(r'^#!.*node', re.IGNORECASE): Language.JAVASCRIPT,
            re.compile(r'^#!.*ruby', re.IGNORECASE): Language.RUBY,
            re.compile(r'^#!.*php', re.IGNORECASE): Language.PHP,
        }
    
    def _build_content_patterns(self) -> Dict[re.Pattern, Language]:
        """构建内容模式到语言的映射"""
        return {
            # Python特征
            re.compile(r'\bdef\s+\w+\s*\(', re.MULTILINE): Language.PYTHON,
            re.compile(r'\bclass\s+\w+.*:', re.MULTILINE): Language.PYTHON,
            re.compile(r'\bimport\s+\w+', re.MULTILINE): Language.PYTHON,
            re.compile(r'\bfrom\s+\w+\s+import', re.MULTILINE): Language.PYTHON,
            
            # Go特征
            re.compile(r'\bfunc\s+\w+\s*\(', re.MULTILINE): Language.GO,
            re.compile(r'\bpackage\s+\w+', re.MULTILINE): Language.GO,
            re.compile(r'\bimport\s*\(', re.MULTILINE): Language.GO,
            
            # Java特征
            re.compile(r'\bpublic\s+class\s+\w+', re.MULTILINE): Language.JAVA,
            re.compile(r'\bpackage\s+[\w.]+;', re.MULTILINE): Language.JAVA,
            re.compile(r'\bimport\s+[\w.*]+;', re.MULTILINE): Language.JAVA,
            
            # TypeScript/JavaScript特征
            re.compile(r'\bfunction\s+\w+\s*\(', re.MULTILINE): Language.JAVASCRIPT,
            re.compile(r'\bconst\s+\w+\s*=', re.MULTILINE): Language.JAVASCRIPT,
            re.compile(r'\blet\s+\w+\s*=', re.MULTILINE): Language.JAVASCRIPT,
            re.compile(r'\bvar\s+\w+\s*=', re.MULTILINE): Language.JAVASCRIPT,
            re.compile(r'\bexport\s+', re.MULTILINE): Language.JAVASCRIPT,
            re.compile(r'\bimport\s+.*\s+from\s+', re.MULTILINE): Language.JAVASCRIPT,
            
            # Rust特征
            re.compile(r'\bfn\s+\w+\s*\(', re.MULTILINE): Language.RUST,
            re.compile(r'\buse\s+[\w:]+;', re.MULTILINE): Language.RUST,
            re.compile(r'\bmod\s+\w+', re.MULTILINE): Language.RUST,
        }
    
    def _build_config_files(self) -> Dict[str, Language]:
        """构建配置文件到语言的映射"""
        return {
            'requirements.txt': Language.PYTHON,
            'setup.py': Language.PYTHON,
            'pyproject.toml': Language.PYTHON,
            'Pipfile': Language.PYTHON,
            'poetry.lock': Language.PYTHON,
            'go.mod': Language.GO,
            'go.sum': Language.GO,
            'pom.xml': Language.JAVA,
            'build.gradle': Language.JAVA,
            'package.json': Language.JAVASCRIPT,
            'tsconfig.json': Language.TYPESCRIPT,
            'Cargo.toml': Language.RUST,
            'Cargo.lock': Language.RUST,
            'composer.json': Language.PHP,
            'Gemfile': Language.RUBY,
            'Podfile': Language.SWIFT,
            'build.gradle.kts': Language.KOTLIN,
        }
    
    def _is_config_file(self, path: Path) -> bool:
        """检查是否为配置文件"""
        return path.name in self._config_files
    
    def _detect_config_language(self, path: Path) -> Language:
        """检测配置文件的语言类型"""
        return self._config_files.get(path.name, Language.UNKNOWN)
    
    def _detect_by_content(self, path: Path) -> Language:
        """通过文件内容检测语言"""
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(4096)  # 只读取前4KB
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    content = f.read(4096)
            except UnicodeDecodeError:
                return Language.UNKNOWN
        
        if not content.strip():
            return Language.UNKNOWN
        
        # 检查shebang
        lines = content.split('\n')
        if lines and lines[0].startswith('#!'):
            for pattern, language in self._shebang_patterns.items():
                if pattern.match(lines[0]):
                    return language
        
        # 检查内容模式
        language_scores: Dict[Language, int] = {lang: 0 for lang in Language}
        
        for pattern, language in self._content_patterns.items():
            matches = len(pattern.findall(content))
            language_scores[language] += matches
        
        # 返回得分最高的语言
        if language_scores:
            best_language = max(language_scores.items(), key=lambda x: x[1])
            if best_language[1] > 0:
                return best_language[0]
        
        return Language.UNKNOWN
    
    def _should_exclude(self, file_path: str, exclude_patterns: List[str]) -> bool:
        """检查文件是否应该被排除"""
        for pattern in exclude_patterns:
            if re.search(pattern, file_path):
                return True
        return False


# 全局实例
_detector = LanguageDetector()


def detect_language(file_path: str) -> Language:
    """
    检测文件的语言类型（便捷函数）
    
    Args:
        file_path: 文件路径
        
    Returns:
        检测到的语言类型
    """
    return _detector.detect_language(file_path)


def detect_languages_in_directory(directory: str, 
                                exclude_patterns: Optional[List[str]] = None) -> Dict[Language, List[str]]:
    """
    检测目录中所有文件的语言类型（便捷函数）
    
    Args:
        directory: 目录路径
        exclude_patterns: 排除的文件模式列表
        
    Returns:
        按语言分组的文件路径字典
    """
    return _detector.detect_languages_in_directory(directory, exclude_patterns)


def get_supported_languages() -> List[Language]:
    """
    获取支持的语言列表（便捷函数）
    
    Returns:
        支持的语言列表
    """
    return _detector.get_supported_languages() 