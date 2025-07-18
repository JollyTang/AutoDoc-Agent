"""
计算器模块

提供基本的数学运算功能，包括加减乘除和高级数学函数。
"""

import math
from typing import Union, List, Optional


class Calculator:
    """
    计算器类
    
    提供基本的数学运算功能，支持整数和浮点数运算。
    """
    
    def __init__(self, precision: int = 2):
        """
        初始化计算器
        
        Args:
            precision: 小数精度，默认为2位
        """
        self.precision = precision
        self.history: List[str] = []
    
    def add(self, a: Union[int, float], b: Union[int, float]) -> float:
        """
        加法运算
        
        Args:
            a: 第一个数
            b: 第二个数
            
        Returns:
            两数之和
            
        Example:
            >>> calc = Calculator()
            >>> calc.add(5, 3)
            8.0
        """
        result = a + b
        self._record_operation(f"{a} + {b} = {result}")
        return round(result, self.precision)
    
    def subtract(self, a: Union[int, float], b: Union[int, float]) -> float:
        """
        减法运算
        
        Args:
            a: 被减数
            b: 减数
            
        Returns:
            两数之差
        """
        result = a - b
        self._record_operation(f"{a} - {b} = {result}")
        return round(result, self.precision)
    
    def multiply(self, a: Union[int, float], b: Union[int, float]) -> float:
        """
        乘法运算
        
        Args:
            a: 第一个数
            b: 第二个数
            
        Returns:
            两数之积
        """
        result = a * b
        self._record_operation(f"{a} * {b} = {result}")
        return round(result, self.precision)
    
    def divide(self, a: Union[int, float], b: Union[int, float]) -> Optional[float]:
        """
        除法运算
        
        Args:
            a: 被除数
            b: 除数
            
        Returns:
            两数之商，如果除数为0则返回None
            
        Raises:
            ValueError: 当除数为0时抛出异常
        """
        if b == 0:
            raise ValueError("除数不能为0")
        
        result = a / b
        self._record_operation(f"{a} / {b} = {result}")
        return round(result, self.precision)
    
    def power(self, base: Union[int, float], exponent: Union[int, float]) -> float:
        """
        幂运算
        
        Args:
            base: 底数
            exponent: 指数
            
        Returns:
            base的exponent次方
        """
        result = math.pow(base, exponent)
        self._record_operation(f"{base} ^ {exponent} = {result}")
        return round(result, self.precision)
    
    def sqrt(self, x: Union[int, float]) -> Optional[float]:
        """
        平方根运算
        
        Args:
            x: 要计算平方根的数
            
        Returns:
            平方根，如果输入为负数则返回None
        """
        if x < 0:
            return None
        
        result = math.sqrt(x)
        self._record_operation(f"√{x} = {result}")
        return round(result, self.precision)
    
    def get_history(self) -> List[str]:
        """
        获取计算历史
        
        Returns:
            计算历史记录列表
        """
        return self.history.copy()
    
    def clear_history(self) -> None:
        """清空计算历史"""
        self.history.clear()
    
    def _record_operation(self, operation: str) -> None:
        """
        记录计算操作
        
        Args:
            operation: 操作描述
        """
        self.history.append(operation)


def calculate_expression(expression: str) -> Optional[float]:
    """
    计算数学表达式
    
    支持基本的四则运算和括号。
    
    Args:
        expression: 数学表达式字符串
        
    Returns:
        计算结果，如果表达式无效则返回None
        
    Example:
        >>> calculate_expression("2 + 3 * 4")
        14.0
    """
    try:
        # 注意：这里使用eval仅用于演示，实际应用中应使用更安全的表达式解析器
        result = eval(expression)
        return float(result) if isinstance(result, (int, float)) else None
    except (ValueError, SyntaxError, ZeroDivisionError):
        return None


# 便捷函数
def add(a: Union[int, float], b: Union[int, float]) -> float:
    """便捷加法函数"""
    return Calculator().add(a, b)


def subtract(a: Union[int, float], b: Union[int, float]) -> float:
    """便捷减法函数"""
    return Calculator().subtract(a, b)


def multiply(a: Union[int, float], b: Union[int, float]) -> float:
    """便捷乘法函数"""
    return Calculator().multiply(a, b)


def divide(a: Union[int, float], b: Union[int, float]) -> Optional[float]:
    """便捷除法函数"""
    return Calculator().divide(a, b) 