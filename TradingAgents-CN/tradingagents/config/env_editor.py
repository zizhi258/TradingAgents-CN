#!/usr/bin/env python3
"""
环境变量(.env)编辑器工具
提供读取、写入和管理.env文件的功能
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import re


def read_env(path: Path) -> Tuple[str, Dict[str, str]]:
    """读取.env文件并返回原始文本和键值对
    
    Args:
        path: .env文件路径
        
    Returns:
        (raw_text, kv_dict): 原始文本和解析的键值对
    """
    if not path.exists():
        return "", {}
    
    try:
        raw_text = path.read_text(encoding='utf-8')
        kv_dict = {}
        
        # 解析键值对，支持引号包围的值
        for line in raw_text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # 匹配 KEY=VALUE 格式
            match = re.match(r'^([A-Z0-9_]+)\s*=\s*(.*)$', line)
            if match:
                key = match.group(1)
                value = match.group(2).strip()
                
                # 移除引号
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                kv_dict[key] = value
                
        return raw_text, kv_dict
    except Exception as e:
        print(f"读取.env文件错误: {e}")
        return "", {}


def merge_and_write_env(path: Path, raw_text: str, updates: Dict[str, str], 
                       remove: List[str] = []) -> None:
    """更新或删除键值对并写回.env文件
    
    Args:
        path: .env文件路径
        raw_text: 原始文件内容
        updates: 要更新的键值对
        remove: 要删除的键名列表
    """
    lines = raw_text.splitlines() if raw_text else []
    new_lines = []
    processed_keys = set()
    
    # 处理现有行
    for line in lines:
        original_line = line
        line = line.strip()
        
        # 保留注释和空行
        if not line or line.startswith('#'):
            new_lines.append(original_line)
            continue
            
        # 解析键值对
        match = re.match(r'^([A-Z0-9_]+)\s*=\s*(.*)$', line)
        if match:
            key = match.group(1)
            
            # 如果键在删除列表中，跳过
            if key in remove:
                continue
                
            # 如果键在更新列表中，使用新值
            if key in updates:
                new_value = updates[key]
                # 如果值包含空格或特殊字符，用引号包围
                if ' ' in new_value or any(c in new_value for c in ['$', '"', "'"]):
                    new_value = f'"{new_value}"'
                new_lines.append(f"{key}={new_value}")
                processed_keys.add(key)
            else:
                # 保留原有值
                new_lines.append(original_line)
        else:
            # 不匹配的行保留原样
            new_lines.append(original_line)
    
    # 添加新的键值对
    for key, value in updates.items():
        if key not in processed_keys:
            # 如果值包含空格或特殊字符，用引号包围
            if ' ' in value or any(c in value for c in ['$', '"', "'"]):
                value = f'"{value}"'
            new_lines.append(f"{key}={value}")
    
    # 写回文件
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        final_content = '\n'.join(new_lines)
        if final_content and not final_content.endswith('\n'):
            final_content += '\n'
        path.write_text(final_content, encoding='utf-8')
    except Exception as e:
        raise Exception(f"写入.env文件失败: {e}")


def get_effective_env_value(key: str, env_file_value: Optional[str] = None) -> str:
    """获取环境变量的实际生效值
    
    Args:
        key: 环境变量键名
        env_file_value: .env文件中的值
        
    Returns:
        实际生效的值（优先级：系统环境变量 > .env文件）
    """
    # 系统环境变量优先
    system_value = os.environ.get(key)
    if system_value:
        return system_value
    
    return env_file_value or ""


def mask_secret_value(value: str) -> str:
    """遮蔽敏感值，只显示后4位
    
    Args:
        value: 原始值
        
    Returns:
        遮蔽后的值
    """
    if not value:
        return ""
    
    if len(value) <= 4:
        return "***"
    
    return "***" + value[-4:]


def validate_env_value(key: str, value: str, field_type: str) -> Tuple[bool, str]:
    """验证环境变量值的格式
    
    Args:
        key: 键名
        value: 值
        field_type: 字段类型
        
    Returns:
        (is_valid, error_message)
    """
    if not value.strip():
        if field_type == "secret":
            return True, ""  # 密钥可以为空
        return False, "值不能为空"
    
    if field_type == "bool":
        if value.lower() not in ["true", "false"]:
            return False, "布尔值必须是 true 或 false"
            
    elif field_type == "int":
        try:
            int(value)
        except ValueError:
            return False, "必须是整数"
            
    elif field_type == "float":
        try:
            float(value)
        except ValueError:
            return False, "必须是数字"
    
    return True, ""