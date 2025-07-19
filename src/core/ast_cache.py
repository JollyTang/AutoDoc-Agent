"""
AST 缓存机制

提供文件级别的 AST 解析结果缓存，提高重复解析的性能。
"""

import os
import json
import hashlib
import pickle
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    file_path: str
    file_hash: str
    file_size: int
    last_modified: float
    ast_data: Any
    created_at: float
    expires_at: Optional[float] = None


class ASTCache:
    """
    AST 缓存管理器
    
    提供文件级别的 AST 解析结果缓存，支持：
    - 文件内容哈希验证
    - 文件大小和修改时间验证
    - 缓存过期机制
    - 多种存储后端（内存、文件）
    """
    
    def __init__(self, cache_dir: Optional[str] = None, 
                 max_size: int = 1000, 
                 ttl: Optional[int] = None):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录路径，None 表示使用内存缓存
            max_size: 最大缓存条目数
            ttl: 缓存生存时间（秒），None 表示永不过期
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.max_size = max_size
        self.ttl = ttl
        
        # 内存缓存
        self._memory_cache: Dict[str, CacheEntry] = {}
        
        # 初始化缓存目录
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"AST缓存目录: {self.cache_dir}")
    
    def _get_file_hash(self, file_path: str) -> str:
        """计算文件内容的哈希值"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.warning(f"计算文件哈希失败 {file_path}: {e}")
            return ""
    
    def _get_file_info(self, file_path: str) -> tuple[str, int, float]:
        """获取文件信息：哈希、大小、修改时间"""
        try:
            stat = os.stat(file_path)
            file_hash = self._get_file_hash(file_path)
            return file_hash, stat.st_size, stat.st_mtime
        except Exception as e:
            logger.warning(f"获取文件信息失败 {file_path}: {e}")
            return "", 0, 0
    
    def _get_cache_key(self, file_path: str) -> str:
        """生成缓存键"""
        return hashlib.md5(file_path.encode()).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.cache"
    
    def _is_cache_valid(self, entry: CacheEntry, file_path: str) -> bool:
        """检查缓存是否有效"""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return False
            
            # 获取当前文件信息
            current_hash, current_size, current_mtime = self._get_file_info(file_path)
            
            # 检查文件哈希
            if entry.file_hash != current_hash:
                return False
            
            # 检查文件大小
            if entry.file_size != current_size:
                return False
            
            # 检查修改时间
            if entry.last_modified != current_mtime:
                return False
            
            # 检查是否过期
            if entry.expires_at and datetime.now().timestamp() > entry.expires_at:
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"检查缓存有效性失败 {file_path}: {e}")
            return False
    
    def get(self, file_path: str) -> Optional[Any]:
        """
        获取缓存的 AST 数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            缓存的 AST 数据，如果缓存无效或不存在则返回 None
        """
        try:
            cache_key = self._get_cache_key(file_path)
            
            # 先从内存缓存获取
            if cache_key in self._memory_cache:
                entry = self._memory_cache[cache_key]
                if self._is_cache_valid(entry, file_path):
                    logger.debug(f"从内存缓存获取: {file_path}")
                    return entry.ast_data
                else:
                    # 缓存无效，从内存中删除
                    del self._memory_cache[cache_key]
            
            # 从文件缓存获取
            if self.cache_dir:
                cache_file = self._get_cache_file_path(cache_key)
                if cache_file.exists():
                    try:
                        with open(cache_file, 'rb') as f:
                            entry = pickle.load(f)
                        
                        if self._is_cache_valid(entry, file_path):
                            # 加载到内存缓存
                            self._memory_cache[cache_key] = entry
                            logger.debug(f"从文件缓存获取: {file_path}")
                            return entry.ast_data
                        else:
                            # 缓存无效，删除文件
                            cache_file.unlink()
                    except Exception as e:
                        logger.warning(f"读取文件缓存失败 {file_path}: {e}")
                        if cache_file.exists():
                            cache_file.unlink()
            
            return None
            
        except Exception as e:
            logger.error(f"获取缓存失败 {file_path}: {e}")
            return None
    
    def set(self, file_path: str, ast_data: Any) -> bool:
        """
        设置缓存
        
        Args:
            file_path: 文件路径
            ast_data: AST 数据
            
        Returns:
            是否成功设置缓存
        """
        try:
            # 获取文件信息
            file_hash, file_size, last_modified = self._get_file_info(file_path)
            if not file_hash:
                return False
            
            # 创建缓存条目
            now = datetime.now().timestamp()
            expires_at = now + self.ttl if self.ttl else None
            
            entry = CacheEntry(
                file_path=file_path,
                file_hash=file_hash,
                file_size=file_size,
                last_modified=last_modified,
                ast_data=ast_data,
                created_at=now,
                expires_at=expires_at
            )
            
            cache_key = self._get_cache_key(file_path)
            
            # 设置内存缓存
            self._memory_cache[cache_key] = entry
            
            # 限制内存缓存大小
            if len(self._memory_cache) > self.max_size:
                self._evict_oldest()
            
            # 设置文件缓存
            if self.cache_dir:
                cache_file = self._get_cache_file_path(cache_key)
                try:
                    with open(cache_file, 'wb') as f:
                        pickle.dump(entry, f)
                    logger.debug(f"设置文件缓存: {file_path}")
                except Exception as e:
                    logger.warning(f"写入文件缓存失败 {file_path}: {e}")
            
            logger.debug(f"设置缓存: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"设置缓存失败 {file_path}: {e}")
            return False
    
    def _evict_oldest(self):
        """驱逐最旧的缓存条目"""
        if not self._memory_cache:
            return
        
        # 按创建时间排序，删除最旧的
        oldest_key = min(
            self._memory_cache.keys(),
            key=lambda k: self._memory_cache[k].created_at
        )
        
        del self._memory_cache[oldest_key]
        logger.debug(f"驱逐缓存条目: {oldest_key}")
    
    def invalidate(self, file_path: str) -> bool:
        """
        使缓存失效
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功使缓存失效
        """
        try:
            cache_key = self._get_cache_key(file_path)
            
            # 从内存缓存删除
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
            
            # 从文件缓存删除
            if self.cache_dir:
                cache_file = self._get_cache_file_path(cache_key)
                if cache_file.exists():
                    cache_file.unlink()
            
            logger.debug(f"使缓存失效: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"使缓存失效失败 {file_path}: {e}")
            return False
    
    def clear(self) -> bool:
        """
        清空所有缓存
        
        Returns:
            是否成功清空缓存
        """
        try:
            # 清空内存缓存
            self._memory_cache.clear()
            
            # 清空文件缓存
            if self.cache_dir and self.cache_dir.exists():
                for cache_file in self.cache_dir.glob("*.cache"):
                    cache_file.unlink()
            
            logger.info("清空所有缓存")
            return True
            
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        try:
            stats = {
                "memory_cache_size": len(self._memory_cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "cache_dir": str(self.cache_dir) if self.cache_dir else None,
            }
            
            # 文件缓存统计
            if self.cache_dir and self.cache_dir.exists():
                cache_files = list(self.cache_dir.glob("*.cache"))
                stats["file_cache_size"] = len(cache_files)
                stats["file_cache_size_bytes"] = sum(f.stat().st_size for f in cache_files)
            else:
                stats["file_cache_size"] = 0
                stats["file_cache_size_bytes"] = 0
            
            return stats
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}


# 全局缓存实例
_global_cache: Optional[ASTCache] = None


def get_global_cache() -> ASTCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        # 默认使用项目根目录下的 .autodoc_cache 目录
        cache_dir = Path.cwd() / ".autodoc_cache" / "ast"
        _global_cache = ASTCache(cache_dir=str(cache_dir))
    return _global_cache


def set_global_cache(cache: ASTCache):
    """设置全局缓存实例"""
    global _global_cache
    _global_cache = cache


def clear_global_cache():
    """清空全局缓存"""
    global _global_cache
    if _global_cache:
        _global_cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """获取全局缓存统计信息"""
    cache = get_global_cache()
    return cache.get_stats() 