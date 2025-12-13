"""
工具函数模块
包含通用的辅助函数
"""
import os
import shutil
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def ensure_dir(directory):
    """
    确保目录存在
    
    Args:
        directory: 目录路径
    """
    os.makedirs(directory, exist_ok=True)


def cleanup_old_tasks(temp_dir, keep_days=7):
    """
    清理旧的任务临时文件
    
    Args:
        temp_dir: 临时目录路径
        keep_days: 保留天数
    """
    if not os.path.exists(temp_dir):
        return
    
    cutoff_time = datetime.now() - timedelta(days=keep_days)
    cleaned_count = 0
    
    for task_dir in os.listdir(temp_dir):
        task_path = os.path.join(temp_dir, task_dir)
        
        if not os.path.isdir(task_path):
            continue
        
        # 获取目录修改时间
        mtime = datetime.fromtimestamp(os.path.getmtime(task_path))
        
        if mtime < cutoff_time:
            try:
                shutil.rmtree(task_path)
                cleaned_count += 1
                logger.info(f"已清理过期任务: {task_dir}")
            except Exception as e:
                logger.warning(f"清理失败: {task_dir} - {str(e)}")
    
    if cleaned_count > 0:
        logger.info(f"清理完成，共删除 {cleaned_count} 个过期任务")


def format_duration(seconds):
    """
    格式化时长
    
    Args:
        seconds: 秒数
    
    Returns:
        str: 格式化后的时长字符串
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def get_file_size(filepath):
    """
    获取文件大小（人类可读格式）
    
    Args:
        filepath: 文件路径
    
    Returns:
        str: 文件大小字符串
    """
    if not os.path.exists(filepath):
        return "0B"
    
    size = os.path.getsize(filepath)
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    
    return f"{size:.1f}TB"
