"""
期货 VWAP 价格穿越监控程序
功能：监控期货合约价格与成交量加权均价(VWAP)的关系，穿越时发出声音提醒
配置文件：config.py
"""

import subprocess
import sys
import time
import os
import gc
import math
import io
import wave
import struct
from datetime import datetime
# ==================== 依赖库检查与自动安装 ====================
# 此部分必须在其他所有导入之前执行

import subprocess
import sys
import importlib
from typing import List, Tuple

# 程序所需的依赖库列表
REQUIRED_PACKAGES = [
    "akshare",
    "pygame-ce",  # 安装后导入名称为 pygame
    "schedule",
    "psutil",
    "requests",
]

# 安装时使用的镜像源（国内加速）
PIP_MIRROR = "https://mirrors.aliyun.com/pypi/simple/"


def check_package_installed(package_name: str) -> bool:
    """
    检查包是否已安装
    
    参数:
        package_name: 包名（如 akshare）
    
    返回:
        True=已安装, False=未安装
    """
    # 处理 pygame-ce 的特殊情况：安装包名是 pygame-ce，但导入名是 pygame
    import_name = "pygame" if package_name == "pygame-ce" else package_name
    
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def install_package(package_name: str) -> bool:
    """
    安装指定的包
    
    参数:
        package_name: 包名
    
    返回:
        True=安装成功, False=安装失败
    """
    print(f"  正在安装 {package_name}...", end=" ", flush=True)
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name,
             "-i", PIP_MIRROR,
             "--trusted-host", "mirrors.aliyun.com",
             "--disable-pip-version-check"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            print("✓")
            return True
        else:
            print("✗")
            error_msg = result.stderr[:200] if result.stderr else "未知错误"
            print(f"    错误: {error_msg}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ (超时)")
        return False
    except Exception as e:
        print(f"✗ ({e})")
        return False


def check_and_install_dependencies() -> bool:
    """
    检查并安装所有依赖库
    
    返回:
        True=全部成功, False=有失败
    """
    print("\n" + "=" * 50)
    print("检查程序依赖库...")
    print("=" * 50)
    
    missing = []
    
    # 检查所有必需库
    for package in REQUIRED_PACKAGES:
        if check_package_installed(package):
            print(f"  ✓ {package}")
        else:
            print(f"  ✗ {package} (缺失)")
            missing.append(package)
    
    print("-" * 50)
    
    if not missing:
        print("所有依赖库已安装 ✓")
        print("=" * 50 + "\n")
        return True
    
    print(f"缺失 {len(missing)} 个依赖库，开始自动安装...")
    print("-" * 50)
    
    failed = []
    for package in missing:
        if install_package(package):
            if check_package_installed(package):
                print(f"  ✓ {package} 安装验证通过")
            else:
                print(f"  ✗ {package} 安装验证失败")
                failed.append(package)
        else:
            failed.append(package)
    
    print("-" * 50)
    
    if failed:
        print(f"\n以下库安装失败: {failed}")
        print("\n请手动安装后重新运行程序：")
        for pkg in failed:
            print(f"  pip install {pkg}")
        print("=" * 50 + "\n")
        return False
    else:
        print("所有依赖库安装成功！")
        print("=" * 50 + "\n")
        return True


# 执行依赖检查（必须在其他导入之前）
if not check_and_install_dependencies():
    print("依赖库安装失败，程序无法继续运行")
    print("请检查网络连接后重试")
    input("按 Enter 键退出...")
    sys.exit(1)


# ==================== 依赖检查完成，开始正常导入 ====================

# 导入外部库
import akshare
import pygame
import schedule
import psutil

# 导入配置、日志和声音模块
import config
import logger_config
import sound_manager 

# ==================== 辅助函数 ====================


def update_all_packages():
    """启动时更新所有需要的模块"""
    if not config.AUTO_UPDATE:
        return

    print("\n" + "=" * 50)
    print("检查并更新模块...")
    print("=" * 50)

    packages = ["akshare", "pygame-ce", "schedule", "psutil"]

    for package in packages:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", package, "--upgrade",
                 "-i", "https://mirrors.aliyun.com/pypi/simple/",
                 "--trusted-host", "mirrors.aliyun.com",
                 "--disable-pip-version-check"],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                print(f"  ✓ {package} 已更新")
                logger_config.info(f"模块更新成功: {package}")
            else:
                print(f"  ⚠ {package} 更新失败")
                logger_config.warning(f"模块更新失败: {package}")
        except Exception as e:
            print(f"  ⚠ {package} 更新出错: {e}")
            logger_config.error(f"模块更新出错: {package} - {e}")

    print("=" * 50 + "\n")


def add_to_startup():
    """添加开机自启动"""
    try:
        import autostarter
        
        # autostarter 的 add() 函数只支持 identifier 和 hidden 参数
        autostarter.add(
            __file__,
            identifier=config.STARTUP_IDENTIFIER,
            interpreter=sys.executable,
            hidden=True
        )
        print("✓ 已添加开机自启动")
        logger_config.info("已添加开机自启动")
    except ImportError:
        print("⚠ autostarter 未安装，跳过开机自启动设置")
        print("  如需开机自启动，请运行: pip install autostarter")
        logger_config.warning("autostarter 未安装")
    except TypeError as e:
        # 参数错误，尝试不使用 hidden 参数
        if "hidden" in str(e):
            try:
                import autostarter
                autostarter.add(
                    __file__,
                    identifier=config.STARTUP_IDENTIFIER,
                    interpreter=sys.executable
                )
                print("✓ 已添加开机自启动（无隐藏模式）")
                logger_config.info("已添加开机自启动")
            except Exception as e2:
                print(f"⚠ 添加开机自启动失败: {e2}")
                logger_config.warning(f"添加开机自启动失败: {e2}")
                print_manual_startup_instructions()
        else:
            print(f"⚠ 添加开机自启动失败: {e}")
            logger_config.warning(f"添加开机自启动失败: {e}")
            print_manual_startup_instructions()
    except Exception as e:
        print(f"⚠ 添加开机自启动失败: {e}")
        logger_config.warning(f"添加开机自启动失败: {e}")
        print_manual_startup_instructions()


def print_manual_startup_instructions():
    """打印手动添加开机自启动的说明"""
    print("\n请手动添加开机自启动：")
    print("  1. 按 Win+R 输入: shell:startup")
    print("  2. 创建 start_monitor.bat 文件，内容：")
    print(f"     @echo off")
    print(f"     cd /d {os.path.dirname(os.path.abspath(__file__))}")
    print(f"     start /b {sys.executable.replace('python.exe', 'pythonw.exe')} {os.path.basename(__file__)}")
    print("  3. 将 start_monitor.bat 放入打开的启动文件夹")


def remove_from_startup():
    """移除开机自启动"""
    try:
        import autostarter
        autostarter.remove(config.STARTUP_IDENTIFIER)
        print("✓ 已移除开机自启动")
        logger_config.info("已移除开机自启动")
    except ImportError:
        print("⚠ autostarter 未安装")
    except Exception as e:
        print(f"⚠ 移除失败: {e}")
        logger_config.warning(f"移除开机自启动失败: {e}")
        print("\n请手动删除启动文件夹中的相关快捷方式")
        print("  1. 按 Win+R 输入: shell:startup")
        print("  2. 删除 futures_vwap_monitor 相关的文件")

def restart_program():
    """重启程序"""
    logger_config.log_restart("定时重启")
    print(f"\n[{datetime.now()}] 正在重启程序...")
    time.sleep(1)
    subprocess.Popen([sys.executable] + sys.argv)
    sys.exit(0)


def check_memory_and_restart():
    """检查内存使用，超限则重启"""
    try:
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb > config.MEMORY_LIMIT_MB:
            logger_config.warning(f"内存使用超限: {memory_mb:.1f} MB > {config.MEMORY_LIMIT_MB} MB")
            print(f"\n⚠ 内存使用超限: {memory_mb:.1f} MB > {config.MEMORY_LIMIT_MB} MB")
            print("执行重启...")
            restart_program()
        return memory_mb
    except Exception as e:
        logger_config.error(f"内存检查失败: {e}")
        return 0







# ==================== 监控器主类 ====================


class VWAPMonitor:
    """VWAP 价格穿越监控器"""

    def __init__(self):
        self.symbols = config.SYMBOLS
        self.tolerance = config.TOLERANCE
        self.status_map = {symbol: None for symbol in self.symbols}
        self.cross_count = {symbol: 0 for symbol in self.symbols}
        self.consecutive_failures = {symbol: 0 for symbol in self.symbols}

        self.loop_count = 0
        self.last_gc_time = time.time()
        
        # 修改：使用独立的声音模块
        sound_manager.init_sound(config)
        self.sound = sound_manager.get_sound_manager()

        # 记录启动
        logger_config.log_startup(self.symbols, self.tolerance)
    

    def get_realtime_data(self, symbol, retry_count=0):
        """获取实时数据"""
        start_time = time.time()
        df = None
        
        try:
            df = akshare.futures_zh_minute_sina(symbol=symbol)

            if df is not None and not df.empty:
                latest = float(df['close'].iloc[-1])
                total_turnover = (df['close'] * df['volume']).sum()
                total_volume = df['volume'].sum()
                vwap = total_turnover / total_volume if total_volume > 0 else latest

                elapsed_ms = (time.time() - start_time) * 1000
                
                # 数据恢复时记录
                if self.consecutive_failures[symbol] > 0:
                    logger_config.log_recovery(symbol)

                # DEBUG 级别记录成功数据
                logger_config.debug(f"[数据] {symbol} | 价格:{latest:.2f} 均价:{vwap:.2f} | 耗时:{elapsed_ms:.0f}ms")

                self.consecutive_failures[symbol] = 0
                return latest, vwap
            else:
                raise ValueError("返回空数据")

        except Exception as e:
            self.consecutive_failures[symbol] += 1

            if retry_count < config.MAX_RETRIES:
                wait_time = config.RETRY_DELAY * (retry_count + 1)
                logger_config.log_data_fail(symbol, retry_count + 1, config.MAX_RETRIES, wait_time)
                print(f"  ⚠ {symbol} 获取失败，{wait_time}秒后重试 ({retry_count+1}/{config.MAX_RETRIES})")
                time.sleep(wait_time)
                return self.get_realtime_data(symbol, retry_count + 1)

            logger_config.error(f"[失败] {symbol} 连续 {self.consecutive_failures[symbol]} 次获取失败")
            return None, None
        finally:
            if df is not None:
                del df

    def get_current_status(self, price, vwap):
        """判断当前价格相对于均价的状态"""
        if price > vwap + self.tolerance:
            return "above"
        elif price < vwap - self.tolerance:
            return "below"
        else:
            return "equal"

    def check_status_change(self, symbol, price, vwap):
        """检查状态是否发生变化"""
        current = self.get_current_status(price, vwap)
        last = self.status_map.get(symbol)

        if last is None:
            self.status_map[symbol] = current
            return False, None

        if current != last:
            if (last, current) == ("above", "below"):
                direction = "高于均价 → 低于均价"
            elif (last, current) == ("below", "above"):
                direction = "低于均价 → 高于均价"
            else:
                direction = f"{last} → {current}"

            self.status_map[symbol] = current
            self.cross_count[symbol] += 1
            return True, direction

        return False, None

    def alert(self, symbol, price, vwap, direction):
        """发出提醒"""
        cross_num = self.cross_count[symbol]
        
        # 记录到日志
        logger_config.log_cross(symbol, direction, price, vwap, cross_num)

        # 输出到控制台
        diff = price - vwap
        print(f"\n🔔 {symbol} {direction}")
        print(f"   时间: {datetime.now().strftime('%H:%M:%S')}")
        print(f"   最新价: {price:.2f} | VWAP: {vwap:.2f} | 价差: {diff:+.2f}")
        print(f"   穿越次数: {cross_num}")

        # 根据方向播放对应音效
        if "低于均价 → 高于均价" in direction:
            self.sound.play_up_alert()
        else:
            self.sound.play_down_alert()

    def run_one_cycle(self):
        """执行一次监控循环"""
        loop_start = datetime.now()

        for symbol in self.symbols:
            price, vwap = self.get_realtime_data(symbol)

            if price is not None and vwap is not None:
                changed, direction = self.check_status_change(symbol, price, vwap)
                icon = "▲" if price > vwap else "▼"
                diff = price - vwap

                # 控制台输出
                print(f"[{loop_start.strftime('%H:%M:%S')}] {symbol}: "
                      f"{price:8.2f} | {vwap:8.2f} | {diff:+7.2f} | {icon}")

                if changed and direction:
                    self.alert(symbol, price, vwap, direction)
            else:
                print(f"[{loop_start.strftime('%H:%M:%S')}] {symbol}: 失败[{self.consecutive_failures[symbol]}]")

            time.sleep(config.BATCH_DELAY)

        # 内存管理
        self.loop_count += 1
        current_time = time.time()
        if current_time - self.last_gc_time >= config.GC_INTERVAL:
            gc.collect()
            self.last_gc_time = current_time

            # 每10轮显示一次内存使用
            if self.loop_count % 10 == 0:
                mem_mb = check_memory_and_restart()
                logger_config.log_memory(mem_mb, self.loop_count)

        print("-" * 60)

    def run(self):
        """主循环"""
        print("\n监控已启动，按 Ctrl+C 停止\n")

        try:
            while True:
                # 执行定时任务检查
                schedule.run_pending()

                # 执行监控循环
                self.run_one_cycle()

                # 等待到下一个周期
                time.sleep(config.CHECK_INTERVAL)

        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        """程序关闭时记录日志"""
        logger_config.log_shutdown(self.loop_count, self.cross_count)
        print("\n监控已停止")
        print(f"总循环次数: {self.loop_count}")
        print("穿越统计:", self.cross_count)


def schedule_restart():
    """定时重启任务"""
    logger_config.log_restart("定时重启")
    print(f"[{datetime.now()}] 执行定时重启...")
    restart_program()


def main():
    """主函数"""
    print("=" * 60)
    print("期货 VWAP 监控程序")
    print("=" * 60)
    print(f"启动时间: {datetime.now()}")
    print(f"监控合约: {', '.join(config.SYMBOLS)}")
    print(f"定时重启: {', '.join(config.RESTART_TIMES)}")
    print(f"内存限制: {config.MEMORY_LIMIT_MB} MB")
    
    # 显示提示音配置
    print("\n提示音配置:")
    print(f"  向上突破: {config.UP_ALERT_FREQUENCY}Hz x{config.UP_ALERT_COUNT} 次")
    print(f"  向下突破: {config.DOWN_ALERT_FREQUENCY}Hz x{config.DOWN_ALERT_COUNT} 次")
    print("=" * 60)

    # 1. 配置日志
    logger_config.setup_logging(config)
    logger_config.info("程序启动")

    # 2. 更新模块
    update_all_packages()

    # 3. 添加开机自启动（根据配置决定）
    if config.ENABLE_STARTUP:
        add_to_startup()
    else:
        remove_from_startup()
        print("开机自启动已禁用（可在 config.py 中启用）")
        logger_config.info("开机自启动已禁用")
    # 4. 设置定时重启
    for restart_time in config.RESTART_TIMES:
        getattr(schedule.every().day, "at")(restart_time).do(schedule_restart)
        print(f"✓ 已设置定时重启: {restart_time}")
        logger_config.info(f"已设置定时重启: {restart_time}")

    # 5. 初始化监控器
    monitor = VWAPMonitor()

    # 6. 运行监控
    monitor.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger_config.error(f"程序异常退出: {e}")
        print(f"\n程序异常: {e}")
        raise
