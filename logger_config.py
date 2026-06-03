"""
日志配置模块
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# 全局变量
_logger = None
_config = None


def setup_logging(config):
    """
    配置日志系统
    
    参数:
        config: 配置模块的引用
    """
    global _logger, _config
    
    _config = config
    
    # 创建日志目录
    if not os.path.exists(config.LOG_DIR):
        os.makedirs(config.LOG_DIR)
    
    # 日志格式
    log_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 获取根日志器
    _logger = logging.getLogger()
    _logger.setLevel(config.LOG_LEVEL)
    
    # 清除已有的处理器
    _logger.handlers.clear()
    
    # 文件处理器（自动轮转）
    file_path = os.path.join(config.LOG_DIR, config.LOG_FILE)
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(config.LOG_LEVEL)
    _logger.addHandler(file_handler)
    
    # 控制台处理器
    if config.LOG_CONSOLE_OUTPUT:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        console_handler.setLevel(config.LOG_LEVEL)
        _logger.addHandler(console_handler)
    
    return _logger


def get_logger():
    """获取日志器实例"""
    global _logger
    return _logger


def info(msg):
    """记录 INFO 级别日志"""
    if _logger:
        _logger.info(msg)


def warning(msg):
    """记录 WARNING 级别日志"""
    if _logger:
        _logger.warning(msg)


def error(msg):
    """记录 ERROR 级别日志"""
    if _logger:
        _logger.error(msg)


def debug(msg):
    """记录 DEBUG 级别日志"""
    if _logger:
        _logger.debug(msg)


def log_cross(symbol, direction, price, vwap, cross_num):
    """记录价格穿越"""
    if not _logger:
        return
    diff = price - vwap
    _logger.warning(
        f"[穿越] {symbol} | {direction} | "
        f"价格:{price:.2f} 均价:{vwap:.2f} 价差:{diff:+.2f} | "
        f"第{cross_num}次"
    )


def log_startup(symbols, tolerance):
    """记录程序启动"""
    if not _logger:
        return
    _logger.info("=" * 60)
    _logger.info(f"监控程序启动 | 合约: {', '.join(symbols)} | 容忍度: {tolerance}")
    _logger.info("=" * 60)


def log_shutdown(loop_count, cross_count):
    """记录程序停止"""
    if not _logger:
        return
    _logger.info("=" * 60)
    _logger.info("监控程序停止")
    _logger.info(f"总循环次数: {loop_count}")
    _logger.info(f"穿越统计: {cross_count}")
    _logger.info("=" * 60)


def log_memory(memory_mb, loop_count):
    """记录内存使用"""
    if not _logger:
        return
    _logger.info(f"[内存] 使用: {memory_mb:.1f} MB | 循环次数: {loop_count}")


def log_restart(reason):
    """记录程序重启"""
    if not _logger:
        return
    _logger.warning(f"[重启] {reason}")


def log_recovery(symbol):
    """记录数据恢复"""
    if not _logger:
        return
    _logger.info(f"[恢复] {symbol} 数据恢复正常")


def log_data_fail(symbol, retry_count, max_retries, wait_time):
    """记录数据获取失败重试"""
    if not _logger:
        return
    _logger.warning(f"[重试] {symbol} 获取失败，{wait_time}秒后重试 ({retry_count}/{max_retries})")