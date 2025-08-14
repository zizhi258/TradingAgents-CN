#!/usr/bin/env python3
"""
文件管理服务
处理邮件附件的上传、存储和管理
"""

import os
import hashlib
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union, BinaryIO
import json

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('file_manager')


class FileManager:
    """文件管理服务 - 处理附件上传和存储"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """初始化文件管理器
        
        Args:
            base_dir: 文件存储基础目录，默认为项目数据目录
        """
        self.base_dir = Path(base_dir or os.path.join(os.getcwd(), 'data', 'attachments'))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        self.reports_dir = self.base_dir / 'reports'
        self.charts_dir = self.base_dir / 'charts' 
        self.uploads_dir = self.base_dir / 'uploads'
        self.temp_dir = self.base_dir / 'temp'
        
        for dir_path in [self.reports_dir, self.charts_dir, self.uploads_dir, self.temp_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # 文件元数据存储
        self.metadata_file = self.base_dir / 'metadata.json'
        self.metadata = self._load_metadata()
        
        logger.info(f"📁 文件管理器初始化完成: {self.base_dir}")
    
    def _load_metadata(self) -> Dict:
        """加载文件元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ 加载元数据失败: {e}")
        return {'files': {}}
    
    def _save_metadata(self):
        """保存文件元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"❌ 保存元数据失败: {e}")
    
    def save_file(self, content: Union[bytes, str], filename: str, 
                  category: str = 'upload', metadata: Optional[Dict] = None) -> str:
        """保存文件
        
        Args:
            content: 文件内容
            filename: 文件名
            category: 文件分类 ('report', 'chart', 'upload', 'temp')
            metadata: 额外的元数据
            
        Returns:
            文件ID
        """
        try:
            # 选择存储目录
            category_dirs = {
                'report': self.reports_dir,
                'chart': self.charts_dir, 
                'upload': self.uploads_dir,
                'temp': self.temp_dir
            }
            
            storage_dir = category_dirs.get(category, self.uploads_dir)
            
            # 生成文件ID
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_hash = hashlib.md5(content if isinstance(content, bytes) else content.encode()).hexdigest()[:8]
            file_id = f"{timestamp}_{file_hash}"
            
            # 构建文件路径
            file_path = storage_dir / f"{file_id}_{filename}"
            
            # 保存文件
            if isinstance(content, bytes):
                with open(file_path, 'wb') as f:
                    f.write(content)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # 记录元数据
            file_info = {
                'id': file_id,
                'filename': filename,
                'original_name': filename,
                'path': str(file_path),
                'size': file_path.stat().st_size,
                'mime_type': mimetypes.guess_type(filename)[0],
                'category': category,
                'created_at': datetime.now(),
                'metadata': metadata or {}
            }
            
            self.metadata['files'][file_id] = file_info
            self._save_metadata()
            
            logger.info(f"✅ 文件保存成功: {filename} -> {file_id}")
            return file_id
            
        except Exception as e:
            logger.error(f"❌ 保存文件失败 {filename}: {e}")
            raise
    
    def get_file(self, file_id: str) -> Optional[Dict]:
        """获取文件信息
        
        Args:
            file_id: 文件ID
            
        Returns:
            文件信息字典
        """
        return self.metadata['files'].get(file_id)
    
    def read_file(self, file_id: str) -> Optional[bytes]:
        """读取文件内容
        
        Args:
            file_id: 文件ID
            
        Returns:
            文件内容（字节）
        """
        file_info = self.get_file(file_id)
        if not file_info:
            logger.warning(f"⚠️ 文件不存在: {file_id}")
            return None
        
        file_path = Path(file_info['path'])
        if not file_path.exists():
            logger.warning(f"⚠️ 文件路径不存在: {file_path}")
            return None
        
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"❌ 读取文件失败 {file_id}: {e}")
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """删除文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            是否成功删除
        """
        file_info = self.get_file(file_id)
        if not file_info:
            return False
        
        try:
            file_path = Path(file_info['path'])
            if file_path.exists():
                file_path.unlink()
            
            # 从元数据中移除
            del self.metadata['files'][file_id]
            self._save_metadata()
            
            logger.info(f"✅ 文件删除成功: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 删除文件失败 {file_id}: {e}")
            return False
    
    def list_files(self, category: Optional[str] = None) -> List[Dict]:
        """列出文件
        
        Args:
            category: 文件分类过滤
            
        Returns:
            文件信息列表
        """
        files = list(self.metadata['files'].values())
        
        if category:
            files = [f for f in files if f.get('category') == category]
        
        # 按创建时间排序
        files.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return files
    
    def cleanup_temp_files(self, older_than_hours: int = 24) -> int:
        """清理临时文件
        
        Args:
            older_than_hours: 删除多少小时前的临时文件
            
        Returns:
            删除的文件数量
        """
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            temp_files = [f for f in self.list_files('temp') 
                         if f.get('created_at') < cutoff_time]
            
            deleted_count = 0
            for file_info in temp_files:
                if self.delete_file(file_info['id']):
                    deleted_count += 1
            
            logger.info(f"🧹 清理了 {deleted_count} 个临时文件")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ 清理临时文件失败: {e}")
            return 0
    
    def get_storage_stats(self) -> Dict:
        """获取存储统计信息
        
        Returns:
            存储统计字典
        """
        try:
            stats = {
                'total_files': len(self.metadata['files']),
                'categories': {},
                'total_size': 0,
                'storage_path': str(self.base_dir)
            }
            
            for file_info in self.metadata['files'].values():
                category = file_info.get('category', 'unknown')
                if category not in stats['categories']:
                    stats['categories'][category] = {'count': 0, 'size': 0}
                
                stats['categories'][category]['count'] += 1
                stats['categories'][category]['size'] += file_info.get('size', 0)
                stats['total_size'] += file_info.get('size', 0)
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ 获取存储统计失败: {e}")
            return {}
    
    def create_attachment_for_email(self, file_id: str) -> Optional[Dict]:
        """为邮件创建附件配置
        
        Args:
            file_id: 文件ID
            
        Returns:
            邮件附件配置字典
        """
        file_info = self.get_file(file_id)
        if not file_info:
            return None
        
        file_content = self.read_file(file_id)
        if not file_content:
            return None
        
        return {
            'type': 'content',
            'filename': file_info['filename'],
            'content': file_content
        }