#!/usr/bin/env python3
"""
模块映射生成功能演示脚本

展示如何使用模块映射生成器分析项目结构和依赖关系。
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.module_mapper import generate_project_mapping, export_mapping_to_json, ModuleMapper


def demo_basic_usage():
    """演示基本用法"""
    print("=== 模块映射生成功能演示 ===\n")
    
    # 使用当前项目作为示例
    project_path = project_root
    
    print(f"分析项目: {project_path}")
    print("正在生成项目映射...")
    
    # 生成项目映射，排除一些目录
    exclude_patterns = [
        "__pycache__", ".git", ".pytest_cache", 
        "htmlcov", "node_modules", "venv", ".venv"
    ]
    
    project_mapping = generate_project_mapping(project_path, exclude_patterns)
    
    print(f"✅ 项目映射生成完成！")
    print(f"📊 项目统计:")
    print(f"   - 总文件数: {project_mapping.total_files}")
    print(f"   - 总代码行数: {project_mapping.total_lines}")
    print(f"   - 语言分布: {dict(project_mapping.language_stats)}")
    
    # 获取详细统计信息
    mapper = ModuleMapper()
    stats = mapper.get_module_statistics(project_mapping)
    print(f"   - 平均复杂度: {stats['average_complexity']}")
    print(f"   - 最大复杂度: {stats['max_complexity']}")
    print(f"   - 循环依赖数: {stats['circular_dependencies_count']}")
    print(f"   - 未使用模块数: {stats['unused_modules_count']}")
    
    return project_mapping


def demo_module_analysis(project_mapping):
    """演示模块分析"""
    print("\n=== 模块分析 ===")
    
    # 显示前5个模块的详细信息
    modules = list(project_mapping.modules.items())[:5]
    
    for file_path, module_mapping in modules:
        print(f"\n📁 模块: {Path(file_path).name}")
        print(f"   路径: {file_path}")
        print(f"   语言: {module_mapping.language.value}")
        print(f"   行数: {module_mapping.line_count}")
        print(f"   复杂度: {module_mapping.complexity_score}")
        print(f"   依赖数: {len(module_mapping.dependencies)}")
        print(f"   被依赖数: {len(module_mapping.dependents)}")
        print(f"   导出数: {len(module_mapping.exports)}")
        
        if module_mapping.dependencies:
            print(f"   依赖: {module_mapping.dependencies[:3]}{'...' if len(module_mapping.dependencies) > 3 else ''}")
        
        if module_mapping.exports:
            print(f"   导出: {module_mapping.exports[:3]}{'...' if len(module_mapping.exports) > 3 else ''}")


def demo_dependency_analysis(project_mapping):
    """演示依赖关系分析"""
    print("\n=== 依赖关系分析 ===")
    
    # 显示依赖图
    print(f"📈 依赖图包含 {len(project_mapping.dependency_graph)} 个节点")
    
    # 显示有最多依赖的模块
    max_deps = max(len(deps) for deps in project_mapping.dependency_graph.values())
    if max_deps > 0:
        print(f"🔗 最大依赖数: {max_deps}")
        
        for file_path, deps in project_mapping.dependency_graph.items():
            if len(deps) == max_deps:
                print(f"   模块: {Path(file_path).name} (依赖 {len(deps)} 个模块)")
                break
    
    # 显示循环依赖
    if project_mapping.circular_dependencies:
        print(f"⚠️  发现 {len(project_mapping.circular_dependencies)} 个循环依赖:")
        for i, cycle in enumerate(project_mapping.circular_dependencies[:3]):
            cycle_names = [Path(p).name for p in cycle]
            print(f"   {i+1}. {' -> '.join(cycle_names)}")
    else:
        print("✅ 未发现循环依赖")
    
    # 显示未使用的模块
    if project_mapping.unused_modules:
        print(f"📦 发现 {len(project_mapping.unused_modules)} 个未使用的模块:")
        for file_path in project_mapping.unused_modules[:5]:
            print(f"   - {Path(file_path).name}")
        if len(project_mapping.unused_modules) > 5:
            print(f"   ... 还有 {len(project_mapping.unused_modules) - 5} 个")
    else:
        print("✅ 所有模块都被使用")


def demo_json_export(project_mapping):
    """演示JSON导出功能"""
    print("\n=== JSON导出演示 ===")
    
    # 导出为JSON格式
    json_data = export_mapping_to_json(project_mapping)
    
    # 保存到文件
    output_file = project_root / "examples" / "project_mapping.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 项目映射已导出到: {output_file}")
    print(f"📄 JSON文件大小: {output_file.stat().st_size / 1024:.1f} KB")
    
    # 显示JSON结构
    print("\n📋 JSON数据结构:")
    for key in json_data.keys():
        if isinstance(json_data[key], dict):
            print(f"   {key}: {{...}} ({len(json_data[key])} 项)")
        elif isinstance(json_data[key], list):
            print(f"   {key}: [...] ({len(json_data[key])} 项)")
        else:
            print(f"   {key}: {json_data[key]}")


def demo_complexity_analysis(project_mapping):
    """演示复杂度分析"""
    print("\n=== 复杂度分析 ===")
    
    # 按复杂度排序
    sorted_modules = sorted(
        project_mapping.modules.items(),
        key=lambda x: x[1].complexity_score,
        reverse=True
    )
    
    print("🏆 复杂度最高的5个模块:")
    for i, (file_path, module_mapping) in enumerate(sorted_modules[:5]):
        print(f"   {i+1}. {Path(file_path).name} (复杂度: {module_mapping.complexity_score})")
    
    # 按行数排序
    sorted_by_lines = sorted(
        project_mapping.modules.items(),
        key=lambda x: x[1].line_count,
        reverse=True
    )
    
    print("\n📏 代码行数最多的5个模块:")
    for i, (file_path, module_mapping) in enumerate(sorted_by_lines[:5]):
        print(f"   {i+1}. {Path(file_path).name} ({module_mapping.line_count} 行)")


def main():
    """主函数"""
    try:
        # 基本用法演示
        project_mapping = demo_basic_usage()
        
        # 模块分析演示
        demo_module_analysis(project_mapping)
        
        # 依赖关系分析演示
        demo_dependency_analysis(project_mapping)
        
        # 复杂度分析演示
        demo_complexity_analysis(project_mapping)
        
        # JSON导出演示
        demo_json_export(project_mapping)
        
        print("\n🎉 演示完成！")
        print("\n💡 提示:")
        print("   - 查看生成的 project_mapping.json 文件了解详细数据")
        print("   - 可以使用这些数据生成项目文档和图表")
        print("   - 模块映射功能支持多种编程语言")
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 