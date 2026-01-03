"""
禁用重排功能的快速配置脚本
如果重排模型下载失败，运行此脚本禁用重排功能
"""
import os
from pathlib import Path

def disable_rerank():
    """禁用重排功能"""
    env_file = Path(".env")
    
    # 读取现有配置
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    else:
        lines = []
    
    # 添加或更新配置
    found = False
    for i, line in enumerate(lines):
        if line.startswith("ENABLE_RERANK="):
            lines[i] = "ENABLE_RERANK=false\n"
            found = True
            break
    
    if not found:
        lines.append("\n# 禁用重排功能（如果模型下载失败）\n")
        lines.append("ENABLE_RERANK=false\n")
    
    # 写回文件
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("✓ 已禁用重排功能")
    print("✓ 系统将使用向量检索，不进行重排")
    print("✓ 如需启用，请设置 ENABLE_RERANK=true 并确保重排模型可用")

if __name__ == "__main__":
    disable_rerank()

