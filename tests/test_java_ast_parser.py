"""
Java AST 解析器的单元测试

测试 Java 代码的 AST 解析功能。
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import Optional

from src.core.java_ast_parser import (
    JavaASTParser, JavaModuleInfo, JavaClassInfo, JavaMethodInfo, JavaFieldInfo,
    parse_java_file, parse_java_source, parse_java_directory
)
from src.core.language_detector import Language


class TestJavaASTParser:
    """Java AST解析器测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.parser = JavaASTParser()
    
    def test_parse_simple_class(self):
        """测试解析简单类"""
        source_code = """
package com.example;

import java.util.List;

public class Calculator {
    private int result;
    
    public Calculator() {
        this.result = 0;
    }
    
    public int add(int a, int b) {
        return a + b;
    }
}
"""
        
        result = self.parser.parse_source(source_code, "Calculator.java")
        
        assert result is not None
        assert result.name == "Calculator"
        assert result.package_name == "com.example"
        assert "java.util.List" in result.imports
        assert len(result.classes) == 1
        
        class_info = result.classes[0]
        assert class_info.name == "Calculator"
        assert class_info.is_public
        assert len(class_info.methods) == 2  # 构造函数 + add方法
        assert len(class_info.fields) == 1
    
    def test_parse_interface(self):
        """测试解析接口"""
        source_code = """
package com.example;

public interface MathOperation {
    int calculate(int a, int b);
    
    default int multiply(int a, int b) {
        return a * b;
    }
}
"""
        
        result = self.parser.parse_source(source_code, "MathOperation.java")
        
        assert result is not None
        assert len(result.interfaces) == 1
        
        interface_info = result.interfaces[0]
        assert interface_info.name == "MathOperation"
        assert interface_info.is_interface
        assert interface_info.is_public
        assert len(interface_info.methods) == 2
    
    def test_parse_enum(self):
        """测试解析枚举"""
        source_code = """
package com.example;

public enum Color {
    RED, GREEN, BLUE;
    
    public String getHexCode() {
        switch (this) {
            case RED: return "#FF0000";
            case GREEN: return "#00FF00";
            case BLUE: return "#0000FF";
            default: return "#000000";
        }
    }
}
"""
        
        result = self.parser.parse_source(source_code, "Color.java")
        
        assert result is not None
        assert len(result.enums) == 1
        
        enum_info = result.enums[0]
        assert enum_info.name == "Color"
        assert enum_info.is_public
        assert len(enum_info.methods) == 1
    
    def test_parse_method_with_throws(self):
        """测试解析带异常声明的方法"""
        source_code = """
package com.example;

import java.io.IOException;

public class FileHandler {
    public String readFile(String path) throws IOException {
        // 实现代码
        return "file content";
    }
}
"""
        
        result = self.parser.parse_source(source_code, "FileHandler.java")
        
        assert result is not None
        assert len(result.classes) == 1
        
        class_info = result.classes[0]
        assert len(class_info.methods) == 1
        
        method_info = class_info.methods[0]
        assert method_info.name == "readFile"
        assert method_info.return_type == "String"
        assert "IOException" in method_info.throws_exceptions
    
    def test_parse_static_method(self):
        """测试解析静态方法"""
        source_code = """
package com.example;

public class Utils {
    public static int max(int a, int b) {
        return a > b ? a : b;
    }
    
    private static final String VERSION = "1.0.0";
}
"""
        
        result = self.parser.parse_source(source_code, "Utils.java")
        
        assert result is not None
        assert len(result.classes) == 1
        
        class_info = result.classes[0]
        assert len(class_info.methods) == 1
        
        method_info = class_info.methods[0]
        assert method_info.name == "max"
        assert method_info.is_static
        assert method_info.is_public
        
        assert len(class_info.fields) == 1
        field_info = class_info.fields[0]
        assert field_info.name == "VERSION"
        assert field_info.is_static
        assert field_info.is_final
        assert field_info.is_private
    
    def test_parse_abstract_class(self):
        """测试解析抽象类"""
        source_code = """
package com.example;

public abstract class Shape {
    protected double area;
    
    public abstract double calculateArea();
    
    public double getArea() {
        return area;
    }
}
"""
        
        result = self.parser.parse_source(source_code, "Shape.java")
        
        assert result is not None
        assert len(result.classes) == 1
        
        class_info = result.classes[0]
        assert class_info.name == "Shape"
        assert class_info.is_abstract
        assert class_info.is_public
        
        assert len(class_info.methods) == 2
        abstract_method = next(m for m in class_info.methods if m.name == "calculateArea")
        assert abstract_method.is_abstract
    
    def test_parse_inheritance(self):
        """测试解析继承关系"""
        source_code = """
package com.example;

public class Animal {
    protected String name;
    
    public Animal(String name) {
        this.name = name;
    }
}

public class Dog extends Animal implements Pet {
    private String breed;
    
    public Dog(String name, String breed) {
        super(name);
        this.breed = breed;
    }
    
    @Override
    public void makeSound() {
        System.out.println("Woof!");
    }
}
"""
        
        result = self.parser.parse_source(source_code, "Animal.java")
        
        assert result is not None
        assert len(result.classes) == 2
        
        # 检查Animal类
        animal_class = next(c for c in result.classes if c.name == "Animal")
        assert animal_class.superclass is None
        assert len(animal_class.interfaces) == 0
        
        # 检查Dog类
        dog_class = next(c for c in result.classes if c.name == "Dog")
        assert dog_class.superclass == "Animal"
        assert "Pet" in dog_class.interfaces
    
    def test_parse_constructor(self):
        """测试解析构造函数"""
        source_code = """
package com.example;

public class Person {
    private String name;
    private int age;
    
    public Person() {
        this.name = "Unknown";
        this.age = 0;
    }
    
    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }
}
"""
        
        result = self.parser.parse_source(source_code, "Person.java")
        
        assert result is not None
        assert len(result.classes) == 1
        
        class_info = result.classes[0]
        constructors = [m for m in class_info.methods if m.is_constructor]
        assert len(constructors) == 2
        
        # 检查无参构造函数
        default_constructor = next(c for c in constructors if len(c.parameters) == 0)
        assert default_constructor.is_public
        
        # 检查有参构造函数
        param_constructor = next(c for c in constructors if len(c.parameters) == 2)
        assert param_constructor.is_public
        assert "name" in param_constructor.parameters
        assert "age" in param_constructor.parameters
    
    def test_parse_file(self):
        """测试解析文件"""
        source_code = """
package com.example;

public class TestClass {
    public void test() {
        System.out.println("Hello World");
    }
}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
            f.write(source_code)
            temp_file = f.name
        
        try:
            result = self.parser.parse_file(temp_file)
            assert result is not None
            assert result.name == "TestClass"
            assert len(result.classes) == 1
        finally:
            os.unlink(temp_file)
    
    def test_parse_directory(self):
        """测试解析目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            java_file1 = Path(temp_dir) / "Class1.java"
            java_file1.write_text("""
package com.example;

public class Class1 {
    public void method1() {}
}
""")
            
            java_file2 = Path(temp_dir) / "Class2.java"
            java_file2.write_text("""
package com.example;

public class Class2 {
    public void method2() {}
}
""")
            
            # 创建非Java文件
            non_java_file = Path(temp_dir) / "test.txt"
            non_java_file.write_text("This is not a Java file")
            
            result = self.parser.parse_directory(temp_dir)
            
            assert len(result) == 2
            assert str(java_file1) in result
            assert str(java_file2) in result
            assert str(non_java_file) not in result
    
    def test_parse_with_exclude_patterns(self):
        """测试解析时排除模式"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            java_file1 = Path(temp_dir) / "Class1.java"
            java_file1.write_text("public class Class1 {}")
            
            java_file2 = Path(temp_dir) / "test" / "Class2.java"
            java_file2.parent.mkdir()
            java_file2.write_text("public class Class2 {}")
            
            result = self.parser.parse_directory(temp_dir, exclude_patterns=["test"])
            
            assert len(result) == 1
            assert str(java_file1) in result
            assert str(java_file2) not in result
    
    def test_parse_complex_structure(self):
        """测试解析复杂结构"""
        source_code = """
package com.example;

import java.util.*;
import java.io.IOException;

public class ComplexClass extends BaseClass implements Interface1, Interface2 {
    // 常量
    public static final int MAX_SIZE = 100;
    private static final String DEFAULT_NAME = "default";
    
    // 实例变量
    private List<String> items;
    protected int count;
    public String name;
    
    // 构造函数
    public ComplexClass() {
        this.items = new ArrayList<>();
        this.count = 0;
    }
    
    public ComplexClass(String name) {
        this();
        this.name = name;
    }
    
    // 实例方法
    public void addItem(String item) {
        if (items.size() < MAX_SIZE) {
            items.add(item);
            count++;
        }
    }
    
    public List<String> getItems() {
        return new ArrayList<>(items);
    }
    
    // 静态方法
    public static ComplexClass createDefault() {
        return new ComplexClass(DEFAULT_NAME);
    }
    
    // 抽象方法实现
    @Override
    public void process() throws IOException {
        // 实现代码
    }
    
    // 私有方法
    private void validateItem(String item) {
        if (item == null || item.trim().isEmpty()) {
            throw new IllegalArgumentException("Item cannot be null or empty");
        }
    }
}
"""
        
        result = self.parser.parse_source(source_code, "ComplexClass.java")
        
        assert result is not None
        assert result.package_name == "com.example"
        assert len(result.imports) == 2
        assert "java.util.*" in result.imports
        assert "java.io.IOException" in result.imports
        
        assert len(result.classes) == 1
        class_info = result.classes[0]
        
        assert class_info.name == "ComplexClass"
        assert class_info.superclass == "BaseClass"
        assert "Interface1" in class_info.interfaces
        assert "Interface2" in class_info.interfaces
        assert class_info.is_public
        
        # 检查字段
        assert len(class_info.fields) == 5  # 3个实例变量 + 2个常量
        
        # 检查方法
        assert len(class_info.methods) == 6  # 2个构造函数 + 4个方法
        
        # 检查构造函数
        constructors = [m for m in class_info.methods if m.is_constructor]
        assert len(constructors) == 2
        
        # 检查静态方法
        static_methods = [m for m in class_info.methods if m.is_static]
        assert len(static_methods) == 1
        assert static_methods[0].name == "createDefault"
    
    def test_parse_invalid_java(self):
        """测试解析无效的Java代码"""
        invalid_source = """
This is not valid Java code
"""
        
        result = self.parser.parse_source(invalid_source, "Invalid.java")
        
        # 应该返回None或空的结构
        if result is not None:
            assert len(result.classes) == 0
            assert len(result.interfaces) == 0
            assert len(result.enums) == 0
    
    def test_parse_empty_file(self):
        """测试解析空文件"""
        result = self.parser.parse_source("", "Empty.java")
        
        if result is not None:
            assert result.name == "Empty"
            assert len(result.classes) == 0
            assert len(result.interfaces) == 0
            assert len(result.enums) == 0


class TestJavaASTParserConvenienceFunctions:
    """测试便捷函数"""
    
    def test_parse_java_file_function(self):
        """测试parse_java_file便捷函数"""
        source_code = """
package com.example;

public class TestClass {
    public void test() {}
}
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
            f.write(source_code)
            temp_file = f.name
        
        try:
            result = parse_java_file(temp_file)
            assert result is not None
            assert result.name == "TestClass"
        finally:
            os.unlink(temp_file)
    
    def test_parse_java_source_function(self):
        """测试parse_java_source便捷函数"""
        source_code = """
package com.example;

public class TestClass {
    public void test() {}
}
"""
        
        result = parse_java_source(source_code, "TestClass.java")
        assert result is not None
        assert result.name == "TestClass"
    
    def test_parse_java_directory_function(self):
        """测试parse_java_directory便捷函数"""
        with tempfile.TemporaryDirectory() as temp_dir:
            java_file = Path(temp_dir) / "TestClass.java"
            java_file.write_text("public class TestClass {}")
            
            result = parse_java_directory(temp_dir)
            assert len(result) == 1
            assert str(java_file) in result


if __name__ == "__main__":
    pytest.main([__file__]) 