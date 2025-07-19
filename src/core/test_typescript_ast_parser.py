"""
TypeScript AST解析器的单元测试

测试TypeScript代码解析的各种场景，包括接口、类、函数、类型定义等。
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import Optional

from .typescript_ast_parser import (
    TypeScriptASTParser, TypeScriptModuleInfo, TypeScriptClassInfo, 
    TypeScriptInterfaceInfo, TypeScriptFunctionInfo, TypeScriptPropertyInfo,
    TypeScriptTypeInfo, TypeScriptEnumInfo,
    parse_typescript_file, parse_typescript_source, parse_typescript_directory
)
from .language_detector import Language


class TestTypeScriptASTParser:
    """TypeScript AST解析器测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.parser = TypeScriptASTParser()
    
    def test_parse_simple_interface(self):
        """测试解析简单接口"""
        source_code = """
interface User {
    id: number;
    name: string;
    email?: string;
    
    getFullName(): string;
}
"""
        
        result = self.parser.parse_source(source_code, "User.ts")
        
        assert result is not None
        assert len(result.interfaces) == 1
        
        interface_info = result.interfaces[0]
        assert interface_info.name == "User"
        assert len(interface_info.properties) == 3
        assert len(interface_info.methods) == 1
        
        # 检查属性
        id_property = next(p for p in interface_info.properties if p.name == "id")
        assert id_property.property_type == "number"
        
        email_property = next(p for p in interface_info.properties if p.name == "email")
        assert email_property.is_optional
    
    def test_parse_interface_with_extends(self):
        """测试解析带继承的接口"""
        source_code = """
interface Animal {
    name: string;
    makeSound(): void;
}

interface Dog extends Animal {
    breed: string;
    bark(): void;
}
"""
        
        result = self.parser.parse_source(source_code, "Animal.ts")
        
        assert result is not None
        assert len(result.interfaces) == 2
        
        dog_interface = next(i for i in result.interfaces if i.name == "Dog")
        assert "Animal" in dog_interface.extends
    
    def test_parse_simple_class(self):
        """测试解析简单类"""
        source_code = """
class Calculator {
    private result: number = 0;
    
    constructor() {
        this.result = 0;
    }
    
    public add(a: number, b: number): number {
        return a + b;
    }
    
    private reset(): void {
        this.result = 0;
    }
}
"""
        
        result = self.parser.parse_source(source_code, "Calculator.ts")
        
        assert result is not None
        assert len(result.classes) == 1
        
        class_info = result.classes[0]
        assert class_info.name == "Calculator"
        assert len(class_info.properties) == 1
        assert len(class_info.methods) == 2
        assert len(class_info.constructors) == 1
        
        # 检查属性
        result_property = class_info.properties[0]
        assert result_property.name == "result"
        assert result_property.is_private
        
        # 检查方法
        add_method = next(m for m in class_info.methods if m.name == "add")
        assert add_method.is_public
    
    def test_parse_abstract_class(self):
        """测试解析抽象类"""
        source_code = """
abstract class Shape {
    protected area: number;
    
    abstract calculateArea(): number;
    
    public getArea(): number {
        return this.area;
    }
}
"""
        
        result = self.parser.parse_source(source_code, "Shape.ts")
        
        assert result is not None
        assert len(result.classes) == 1
        
        class_info = result.classes[0]
        assert class_info.name == "Shape"
        assert class_info.is_abstract
        
        # 检查抽象方法
        abstract_method = next(m for m in class_info.methods if m.name == "calculateArea")
        assert abstract_method.is_abstract
    
    def test_parse_class_with_inheritance(self):
        """测试解析带继承的类"""
        source_code = """
class Animal {
    protected name: string;
    
    constructor(name: string) {
        this.name = name;
    }
}

class Dog extends Animal implements Pet {
    private breed: string;
    
    constructor(name: string, breed: string) {
        super(name);
        this.breed = breed;
    }
    
    public bark(): void {
        console.log("Woof!");
    }
}
"""
        
        result = self.parser.parse_source(source_code, "Animal.ts")
        
        assert result is not None
        assert len(result.classes) == 2
        
        # 检查Animal类
        animal_class = next(c for c in result.classes if c.name == "Animal")
        assert animal_class.extends is None
        assert len(animal_class.implements) == 0
        
        # 检查Dog类
        dog_class = next(c for c in result.classes if c.name == "Dog")
        assert dog_class.extends == "Animal"
        assert "Pet" in dog_class.implements
    
    def test_parse_function(self):
        """测试解析函数"""
        source_code = """
export function greet(name: string): string {
    return `Hello, ${name}!`;
}

async function fetchData(url: string): Promise<any> {
    const response = await fetch(url);
    return response.json();
}
"""
        
        result = self.parser.parse_source(source_code, "functions.ts")
        
        assert result is not None
        assert len(result.functions) == 2
        
        # 检查导出的函数
        greet_function = next(f for f in result.functions if f.name == "greet")
        assert greet_function.is_export
        
        # 检查异步函数
        fetch_function = next(f for f in result.functions if f.name == "fetchData")
        assert fetch_function.is_async
    
    def test_parse_type_definition(self):
        """测试解析类型定义"""
        source_code = """
export type UserId = string | number;

type Status = 'pending' | 'approved' | 'rejected';

type ApiResponse<T> = {
    data: T;
    status: number;
    message: string;
};
"""
        
        result = self.parser.parse_source(source_code, "types.ts")
        
        assert result is not None
        assert len(result.types) == 3
        
        # 检查导出的类型
        user_id_type = next(t for t in result.types if t.name == "UserId")
        assert user_id_type.is_export
        assert "string | number" in user_id_type.type_definition
        
        # 检查泛型类型
        api_response_type = next(t for t in result.types if t.name == "ApiResponse")
        assert "T" in api_response_type.type_definition
    
    def test_parse_enum(self):
        """测试解析枚举"""
        source_code = """
export enum Color {
    RED = '#FF0000',
    GREEN = '#00FF00',
    BLUE = '#0000FF'
}

enum Direction {
    NORTH,
    SOUTH,
    EAST,
    WEST
}
"""
        
        result = self.parser.parse_source(source_code, "enums.ts")
        
        assert result is not None
        assert len(result.enums) == 2
        
        # 检查导出的枚举
        color_enum = next(e for e in result.enums if e.name == "Color")
        assert color_enum.is_export
        assert len(color_enum.members) >= 3
        
        # 检查普通枚举
        direction_enum = next(e for e in result.enums if e.name == "Direction")
        assert not direction_enum.is_export
    
    def test_parse_imports_and_exports(self):
        """测试解析导入和导出"""
        source_code = """
import { Component } from 'react';
import * as utils from './utils';
import './styles.css';

export interface User {
    id: number;
    name: string;
}

export default class UserService {
    // 实现代码
}
"""
        
        result = self.parser.parse_source(source_code, "UserService.ts")
        
        assert result is not None
        assert len(result.imports) == 3
        assert "react" in result.imports
        assert "./utils" in result.imports
        assert "./styles.css" in result.imports
        
        assert len(result.exports) >= 1
        assert "User" in result.exports
    
    def test_parse_static_methods_and_properties(self):
        """测试解析静态方法和属性"""
        source_code = """
class MathUtils {
    public static readonly PI: number = 3.14159;
    
    public static max(a: number, b: number): number {
        return a > b ? a : b;
    }
    
    private static validateNumber(n: number): boolean {
        return !isNaN(n);
    }
}
"""
        
        result = self.parser.parse_source(source_code, "MathUtils.ts")
        
        assert result is not None
        assert len(result.classes) == 1
        
        class_info = result.classes[0]
        
        # 检查静态属性
        pi_property = next(p for p in class_info.properties if p.name == "PI")
        assert pi_property.is_static
        assert pi_property.is_public
        assert pi_property.is_readonly
        
        # 检查静态方法
        max_method = next(m for m in class_info.methods if m.name == "max")
        assert max_method.is_static
        assert max_method.is_public
    
    def test_parse_readonly_properties(self):
        """测试解析只读属性"""
        source_code = """
interface Config {
    readonly apiUrl: string;
    readonly timeout: number;
    readonly retries: number;
}

class AppConfig implements Config {
    public readonly apiUrl: string;
    public readonly timeout: number;
    public readonly retries: number;
    
    constructor(apiUrl: string, timeout: number, retries: number) {
        this.apiUrl = apiUrl;
        this.timeout = timeout;
        this.retries = retries;
    }
}
"""
        
        result = self.parser.parse_source(source_code, "Config.ts")
        
        assert result is not None
        assert len(result.interfaces) == 1
        assert len(result.classes) == 1
        
        # 检查接口的只读属性
        interface_info = result.interfaces[0]
        for property_info in interface_info.properties:
            assert property_info.is_readonly
        
        # 检查类的只读属性
        class_info = result.classes[0]
        for property_info in class_info.properties:
            assert property_info.is_readonly
    
    def test_parse_optional_properties(self):
        """测试解析可选属性"""
        source_code = """
interface UserProfile {
    id: number;
    name: string;
    email?: string;
    phone?: string;
    avatar?: string;
}

class User implements UserProfile {
    public id: number;
    public name: string;
    public email?: string;
    public phone?: string;
    public avatar?: string;
    
    constructor(id: number, name: string, email?: string) {
        this.id = id;
        this.name = name;
        this.email = email;
    }
}
"""
        
        result = self.parser.parse_source(source_code, "User.ts")
        
        assert result is not None
        assert len(result.interfaces) == 1
        assert len(result.classes) == 1
        
        # 检查接口的可选属性
        interface_info = result.interfaces[0]
        optional_properties = [p for p in interface_info.properties if p.is_optional]
        assert len(optional_properties) == 3
        
        # 检查类的可选属性
        class_info = result.classes[0]
        optional_properties = [p for p in class_info.properties if p.is_optional]
        assert len(optional_properties) == 3
    
    def test_parse_file(self):
        """测试解析文件"""
        source_code = """
interface TestInterface {
    test(): void;
}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(source_code)
            temp_file = f.name
        
        try:
            result = self.parser.parse_file(temp_file)
            assert result is not None
            assert len(result.interfaces) == 1
        finally:
            os.unlink(temp_file)
    
    def test_parse_directory(self):
        """测试解析目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            ts_file1 = Path(temp_dir) / "Interface1.ts"
            ts_file1.write_text("""
interface Interface1 {
    method1(): void;
}
""")
            
            ts_file2 = Path(temp_dir) / "Class1.ts"
            ts_file2.write_text("""
class Class1 {
    method2(): void {}
}
""")
            
            # 创建非TypeScript文件
            non_ts_file = Path(temp_dir) / "test.txt"
            non_ts_file.write_text("This is not a TypeScript file")
            
            result = self.parser.parse_directory(temp_dir)
            
            assert len(result) == 2
            assert str(ts_file1) in result
            assert str(ts_file2) in result
            assert str(non_ts_file) not in result
    
    def test_parse_with_exclude_patterns(self):
        """测试解析时排除模式"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            ts_file1 = Path(temp_dir) / "Interface1.ts"
            ts_file1.write_text("interface Interface1 {}")
            
            ts_file2 = Path(temp_dir) / "test" / "Interface2.ts"
            ts_file2.parent.mkdir()
            ts_file2.write_text("interface Interface2 {}")
            
            result = self.parser.parse_directory(temp_dir, exclude_patterns=["test"])
            
            assert len(result) == 1
            assert str(ts_file1) in result
            assert str(ts_file2) not in result
    
    def test_parse_complex_structure(self):
        """测试解析复杂结构"""
        source_code = """
import React from 'react';
import { useState, useEffect } from 'react';

export interface User {
    id: number;
    name: string;
    email?: string;
}

export type UserStatus = 'active' | 'inactive' | 'pending';

export enum UserRole {
    ADMIN = 'admin',
    USER = 'user',
    GUEST = 'guest'
}

export abstract class BaseService {
    protected abstract apiUrl: string;
    
    abstract fetchData(): Promise<any>;
    
    protected validateResponse(response: any): boolean {
        return response && response.status === 200;
    }
}

export class UserService extends BaseService {
    protected apiUrl: string = '/api/users';
    
    private cache: Map<number, User> = new Map();
    
    public async fetchData(): Promise<User[]> {
        const response = await fetch(this.apiUrl);
        if (this.validateResponse(response)) {
            return response.json();
        }
        throw new Error('Failed to fetch users');
    }
    
    public getUserById(id: number): User | undefined {
        return this.cache.get(id);
    }
    
    private updateCache(user: User): void {
        this.cache.set(user.id, user);
    }
}

export const createUserService = (): UserService => {
    return new UserService();
};
"""
        
        result = self.parser.parse_source(source_code, "UserService.ts")
        
        assert result is not None
        assert len(result.imports) == 2
        assert "react" in result.imports
        
        assert len(result.exports) >= 4
        assert "User" in result.exports
        assert "UserStatus" in result.exports
        assert "UserRole" in result.exports
        assert "BaseService" in result.exports
        
        assert len(result.interfaces) == 1
        assert len(result.classes) == 2
        assert len(result.types) == 1
        assert len(result.enums) == 1
        assert len(result.functions) == 1
        
        # 检查抽象类
        base_service = next(c for c in result.classes if c.name == "BaseService")
        assert base_service.is_abstract
        
        # 检查继承
        user_service = next(c for c in result.classes if c.name == "UserService")
        assert user_service.extends == "BaseService"
    
    def test_parse_invalid_typescript(self):
        """测试解析无效的TypeScript代码"""
        invalid_source = """
This is not valid TypeScript code
"""
        
        result = self.parser.parse_source(invalid_source, "Invalid.ts")
        
        # 应该返回None或空的结构
        if result is not None:
            assert len(result.interfaces) == 0
            assert len(result.classes) == 0
            assert len(result.functions) == 0
    
    def test_parse_empty_file(self):
        """测试解析空文件"""
        result = self.parser.parse_source("", "Empty.ts")
        
        if result is not None:
            assert result.name == "Empty"
            assert len(result.interfaces) == 0
            assert len(result.classes) == 0
            assert len(result.functions) == 0


class TestTypeScriptASTParserConvenienceFunctions:
    """测试便捷函数"""
    
    def test_parse_typescript_file_function(self):
        """测试parse_typescript_file便捷函数"""
        source_code = """
interface TestInterface {
    test(): void;
}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(source_code)
            temp_file = f.name
        
        try:
            result = parse_typescript_file(temp_file)
            assert result is not None
            assert len(result.interfaces) == 1
        finally:
            os.unlink(temp_file)
    
    def test_parse_typescript_source_function(self):
        """测试parse_typescript_source便捷函数"""
        source_code = """
interface TestInterface {
    test(): void;
}
"""
        
        result = parse_typescript_source(source_code, "TestInterface.ts")
        assert result is not None
        assert len(result.interfaces) == 1
    
    def test_parse_typescript_directory_function(self):
        """测试parse_typescript_directory便捷函数"""
        with tempfile.TemporaryDirectory() as temp_dir:
            ts_file = Path(temp_dir) / "TestInterface.ts"
            ts_file.write_text("interface TestInterface {}")
            
            result = parse_typescript_directory(temp_dir)
            assert len(result) == 1
            assert str(ts_file) in result


if __name__ == "__main__":
    pytest.main([__file__]) 