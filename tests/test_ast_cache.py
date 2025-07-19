"""
AST 缓存机制的单元测试

测试缓存功能的各种场景。
"""

import pytest
import tempfile
import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.ast_cache import (
    ASTCache,
    CacheEntry,
    get_global_cache,
    set_global_cache,
    clear_global_cache,
    get_cache_stats
)


class TestASTCache:
    """AST 缓存测试类"""
    
    def test_create_cache(self):
        """测试创建缓存"""
        # 内存缓存
        cache = ASTCache()
        assert cache.cache_dir is None
        assert cache.max_size == 1000
        assert cache.ttl is None
        assert len(cache._memory_cache) == 0
        
        # 文件缓存
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = ASTCache(cache_dir=temp_dir, max_size=100, ttl=3600)
            assert str(cache.cache_dir) == temp_dir
            assert cache.max_size == 100
            assert cache.ttl == 3600
    
    def test_cache_key_generation(self):
        """测试缓存键生成"""
        cache = ASTCache()
        
        key1 = cache._get_cache_key("/path/to/file.py")
        key2 = cache._get_cache_key("/path/to/file.py")
        key3 = cache._get_cache_key("/different/path/file.py")
        
        assert key1 == key2  # 相同路径生成相同键
        assert key1 != key3  # 不同路径生成不同键
        assert len(key1) == 32  # MD5 哈希长度
    
    def test_file_info_extraction(self):
        """测试文件信息提取"""
        cache = ASTCache()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = f.name
        
        try:
            file_hash, file_size, last_modified = cache._get_file_info(temp_file)
            
            assert len(file_hash) == 32  # MD5 哈希长度
            assert file_size > 0
            assert last_modified > 0
            
        finally:
            os.unlink(temp_file)
    
    def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        cache = ASTCache()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = f.name
        
        try:
            # 测试数据
            test_data = {"functions": [], "classes": [], "imports": []}
            
            # 设置缓存
            result = cache.set(temp_file, test_data)
            assert result is True
            
            # 获取缓存
            cached_data = cache.get(temp_file)
            assert cached_data == test_data
            
            # 验证缓存条目
            cache_key = cache._get_cache_key(temp_file)
            assert cache_key in cache._memory_cache
            
            entry = cache._memory_cache[cache_key]
            assert entry.file_path == temp_file
            assert entry.ast_data == test_data
            
        finally:
            os.unlink(temp_file)
    
    def test_cache_invalidation(self):
        """测试缓存失效"""
        cache = ASTCache()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = f.name
        
        try:
            # 设置缓存
            test_data = {"test": "data"}
            cache.set(temp_file, test_data)
            
            # 验证缓存存在
            assert cache.get(temp_file) == test_data
            
            # 使缓存失效
            result = cache.invalidate(temp_file)
            assert result is True
            
            # 验证缓存已失效
            assert cache.get(temp_file) is None
            
        finally:
            os.unlink(temp_file)
    
    def test_cache_with_file_modification(self):
        """测试文件修改后的缓存失效"""
        cache = ASTCache()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("original content")
            temp_file = f.name
        
        try:
            # 设置缓存
            test_data = {"test": "data"}
            cache.set(temp_file, test_data)
            
            # 验证缓存存在
            assert cache.get(temp_file) == test_data
            
            # 修改文件内容
            time.sleep(0.1)  # 确保修改时间不同
            with open(temp_file, 'w') as f:
                f.write("modified content")
            
            # 验证缓存已失效
            assert cache.get(temp_file) is None
            
        finally:
            os.unlink(temp_file)
    
    def test_cache_expiration(self):
        """测试缓存过期"""
        # 创建短期缓存（1秒）
        cache = ASTCache(ttl=1)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = f.name
        
        try:
            # 设置缓存
            test_data = {"test": "data"}
            cache.set(temp_file, test_data)
            
            # 立即获取应该成功
            assert cache.get(temp_file) == test_data
            
            # 等待过期
            time.sleep(1.1)
            
            # 获取应该失败
            assert cache.get(temp_file) is None
            
        finally:
            os.unlink(temp_file)
    
    def test_cache_size_limit(self):
        """测试缓存大小限制"""
        cache = ASTCache(max_size=2)
        
        # 创建多个临时文件
        temp_files = []
        try:
            for i in range(3):
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                    f.write(f"content {i}")
                    temp_files.append(f.name)
                
                # 设置缓存
                cache.set(temp_files[i], {"data": i})
            
            # 验证只有最新的2个文件在缓存中
            assert len(cache._memory_cache) == 2
            
            # 第一个文件应该被驱逐
            assert cache.get(temp_files[0]) is None
            
            # 后面的文件应该还在
            assert cache.get(temp_files[1]) is not None
            assert cache.get(temp_files[2]) is not None
            
        finally:
            for temp_file in temp_files:
                os.unlink(temp_file)
    
    def test_file_cache_persistence(self):
        """测试文件缓存持久化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            cache = ASTCache(cache_dir=temp_dir)
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write("test content")
                temp_file = f.name
            
            try:
                # 设置缓存
                test_data = {"test": "data"}
                cache.set(temp_file, test_data)
                
                # 创建新的缓存实例（模拟重启）
                new_cache = ASTCache(cache_dir=temp_dir)
                
                # 应该能从文件缓存恢复
                cached_data = new_cache.get(temp_file)
                assert cached_data == test_data
                
            finally:
                os.unlink(temp_file)
    
    def test_cache_clear(self):
        """测试清空缓存"""
        cache = ASTCache()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = f.name
        
        try:
            # 设置缓存
            test_data = {"test": "data"}
            cache.set(temp_file, test_data)
            
            # 验证缓存存在
            assert cache.get(temp_file) == test_data
            
            # 清空缓存
            result = cache.clear()
            assert result is True
            
            # 验证缓存已清空
            assert cache.get(temp_file) is None
            assert len(cache._memory_cache) == 0
            
        finally:
            os.unlink(temp_file)
    
    def test_cache_stats(self):
        """测试缓存统计信息"""
        cache = ASTCache(max_size=100, ttl=3600)
        
        stats = cache.get_stats()
        
        assert "memory_cache_size" in stats
        assert "max_size" in stats
        assert "ttl" in stats
        assert "cache_dir" in stats
        assert "file_cache_size" in stats
        assert "file_cache_size_bytes" in stats
        
        assert stats["memory_cache_size"] == 0
        assert stats["max_size"] == 100
        assert stats["ttl"] == 3600
        assert stats["cache_dir"] is None
        assert stats["file_cache_size"] == 0
        assert stats["file_cache_size_bytes"] == 0


class TestGlobalCache:
    """全局缓存测试类"""
    
    def test_global_cache_singleton(self):
        """测试全局缓存单例模式"""
        cache1 = get_global_cache()
        cache2 = get_global_cache()
        
        assert cache1 is cache2
    
    def test_set_global_cache(self):
        """测试设置全局缓存"""
        # 保存原始缓存
        original_cache = get_global_cache()
        
        # 创建新缓存
        new_cache = ASTCache()
        set_global_cache(new_cache)
        
        # 验证已更新
        assert get_global_cache() is new_cache
        
        # 恢复原始缓存
        set_global_cache(original_cache)
    
    def test_clear_global_cache(self):
        """测试清空全局缓存"""
        cache = get_global_cache()
        
        # 设置一些数据
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = f.name
        
        try:
            cache.set(temp_file, {"test": "data"})
            assert cache.get(temp_file) is not None
            
            # 清空缓存
            clear_global_cache()
            
            # 验证已清空
            assert cache.get(temp_file) is None
            
        finally:
            os.unlink(temp_file)
    
    def test_get_cache_stats(self):
        """测试获取缓存统计信息"""
        stats = get_cache_stats()
        
        assert isinstance(stats, dict)
        assert "memory_cache_size" in stats
        assert "max_size" in stats


class TestCacheEdgeCases:
    """缓存边界情况测试类"""
    
    def test_cache_nonexistent_file(self):
        """测试不存在的文件"""
        cache = ASTCache()
        
        # 尝试获取不存在的文件
        result = cache.get("/nonexistent/file.py")
        assert result is None
        
        # 尝试设置不存在的文件
        result = cache.set("/nonexistent/file.py", {"test": "data"})
        assert result is False
    
    def test_cache_empty_file(self):
        """测试空文件"""
        cache = ASTCache()
        
        # 创建空文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_file = f.name
        
        try:
            # 设置缓存
            test_data = {"test": "data"}
            result = cache.set(temp_file, test_data)
            assert result is True
            
            # 获取缓存
            cached_data = cache.get(temp_file)
            assert cached_data == test_data
            
        finally:
            os.unlink(temp_file)
    
    def test_cache_large_data(self):
        """测试大数据缓存"""
        cache = ASTCache()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = f.name
        
        try:
            # 创建大数据
            large_data = {
                "functions": [{"name": f"func_{i}", "code": "x" * 1000} for i in range(100)],
                "classes": [{"name": f"class_{i}", "methods": ["x" * 1000]} for i in range(50)]
            }
            
            # 设置缓存
            result = cache.set(temp_file, large_data)
            assert result is True
            
            # 获取缓存
            cached_data = cache.get(temp_file)
            assert cached_data == large_data
            
        finally:
            os.unlink(temp_file)
    
    def test_cache_concurrent_access(self):
        """测试并发访问"""
        cache = ASTCache()
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = f.name
        
        try:
            # 模拟并发设置和获取
            test_data = {"test": "data"}
            
            # 同时设置和获取（在实际使用中应该使用锁）
            cache.set(temp_file, test_data)
            cached_data = cache.get(temp_file)
            
            assert cached_data == test_data
            
        finally:
            os.unlink(temp_file) 