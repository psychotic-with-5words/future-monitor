"""
集成测试程序 - 测试期货VWAP监控程序的所有功能
测试项目：提示音、日志记录、数据获取、内存监控、配置文件
运行后显示菜单，通过输入数字选择测试项
"""

import sys
import os
import time
from datetime import datetime

# ==================== 导入配置 ====================
# 确保能导入同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入配置和日志模块
import config
import logger_config
import sound_manager

# ==================== 测试配置 ====================
TEST_SYMBOL = "AG2608"  # 测试用合约


# ==================== 测试类 ====================

class IntegrationTester:
    """集成测试器"""
    
    def __init__(self):
        self.test_results = {}
        self.test_symbol = TEST_SYMBOL
    
    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title):
        """打印测试标题"""
        print("\n" + "=" * 60)
        print(f"【{title}】")
        print("=" * 60)
    
    def print_result(self, test_name, passed, message=""):
        """打印测试结果"""
        status = "✓ 通过" if passed else "✗ 失败"
        self.test_results[test_name] = passed
        print(f"{status}: {test_name}")
        if message:
            print(f"    {message}")
    
    def wait_for_enter(self):
        """等待用户按回车"""
        input("\n按 Enter 键继续...")
    
    # ==================== 测试1: 配置文件测试 ====================
    
    def test_config(self):
        """测试配置文件完整性"""
        self.print_header("测试1: 配置文件完整性")
        
        required_attrs = [
            'SYMBOLS', 'CHECK_INTERVAL', 'BATCH_DELAY',
            'MAX_RETRIES', 'RETRY_DELAY', 'TOLERANCE',
            'RESTART_TIMES', 'MEMORY_LIMIT_MB', 'GC_INTERVAL',
            'AUTO_UPDATE', 'LOG_DIR', 'LOG_FILE', 'LOG_LEVEL',
            'SOUND_ENABLED', 'SOUND_MODE',
            'UP_ALERT_FREQUENCY', 'UP_ALERT_DURATION', 'UP_ALERT_COUNT',
            'UP_ALERT_INTERVAL', 'UP_ALERT_VOLUME',
            'DOWN_ALERT_FREQUENCY', 'DOWN_ALERT_DURATION', 'DOWN_ALERT_COUNT',
            'DOWN_ALERT_INTERVAL', 'DOWN_ALERT_VOLUME',
            'WARMUP_ENABLED', 'STARTUP_IDENTIFIER'
        ]
        
        missing = []
        present = []
        
        for attr in required_attrs:
            if hasattr(config, attr):
                value = getattr(config, attr)
                present.append(f"{attr}={value}")
            else:
                missing.append(attr)
        
        if missing:
            print(f"\n缺失的配置项: {missing}")
            self.print_result("配置文件完整性", False, f"缺失 {len(missing)} 项")
        else:
            print("\n配置项检查通过:")
            for item in present[:12]:
                print(f"  ✓ {item}")
            if len(present) > 12:
                print(f"  ... 共 {len(present)} 项配置")
            self.print_result("配置文件完整性", True, f"{len(present)} 项配置完整")
        
        # 显示当前配置摘要
        print("\n当前配置摘要:")
        print(f"  监控合约: {', '.join(config.SYMBOLS)}")
        print(f"  检查间隔: {config.CHECK_INTERVAL} 秒")
        print(f"  定时重启: {', '.join(config.RESTART_TIMES)}")
        print(f"  内存限制: {config.MEMORY_LIMIT_MB} MB")
        print(f"  声音模式: {config.SOUND_MODE}")
        if config.SOUND_MODE == "synthesized":
            print(f"  向上突破音效: {config.UP_ALERT_FREQUENCY}Hz x{config.UP_ALERT_COUNT}")
            print(f"  向下突破音效: {config.DOWN_ALERT_FREQUENCY}Hz x{config.DOWN_ALERT_COUNT}")
        else:
            print(f"  向上突破文件: {config.UP_ALERT_FILE}")
            print(f"  向下突破文件: {config.DOWN_ALERT_FILE}")
        
        self.wait_for_enter()
        return len(missing) == 0
    
    # ==================== 测试2: 日志功能测试 ====================
    
    def test_logging(self):
        """测试日志记录功能"""
        self.print_header("测试2: 日志记录功能")
        
        try:
            # 初始化日志
            logger_config.setup_logging(config)
            
            # 测试各种日志级别
            test_time = datetime.now().strftime("%H:%M:%S")
            
            print("\n正在写入测试日志...")
            
            logger_config.info(f"[测试] INFO级别日志 - {test_time}")
            logger_config.warning(f"[测试] WARNING级别日志 - {test_time}")
            logger_config.error(f"[测试] ERROR级别日志 - {test_time}")
            logger_config.debug(f"[测试] DEBUG级别日志 - {test_time}")
            
            # 测试专用日志函数
            logger_config.log_startup(["TEST"], 0.5)
            logger_config.log_cross("TEST", "高于均价 → 低于均价", 100.0, 101.5, 1)
            logger_config.log_memory(85.5, 10)
            logger_config.log_restart("测试重启")
            logger_config.log_recovery("TEST")
            logger_config.log_data_fail("TEST", 1, 3, 2)
            logger_config.log_shutdown(100, {"TEST": 2})
            
            print("✓ 日志写入完成")
            
            # 检查日志文件是否创建
            log_file_path = os.path.join(config.LOG_DIR, config.LOG_FILE)
            
            if os.path.exists(log_file_path):
                file_size = os.path.getsize(log_file_path)
                print(f"\n日志文件: {log_file_path}")
                print(f"文件大小: {file_size} 字节")
                
                # 读取最后几行
                with open(log_file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    last_lines = lines[-6:] if len(lines) >= 6 else lines
                
                print("\n最近6条日志记录:")
                for line in last_lines:
                    print(f"  {line.strip()}")
                
                self.print_result("日志文件创建", True, f"大小 {file_size} 字节")
                self.print_result("日志写入成功", True, f"共 {len(lines)} 条记录")
            else:
                self.print_result("日志文件创建", False, "文件未找到")
                self.print_result("日志写入成功", False, "日志文件不存在")
            
        except Exception as e:
            self.print_result("日志功能", False, str(e))
        
        self.wait_for_enter()
        return True
    
    # ==================== 测试3: 提示音测试 ====================
    
    def test_sound(self):
        """测试提示音功能（使用独立 sound_manager 模块）"""
        self.print_header("测试3: 提示音功能")
        
        print("\n⚠ 请确保音量已开启，仔细听以下提示音...")
        print("=" * 40)
        
        try:
            # 初始化声音模块
            sound_manager.init_sound(config)
            sound = sound_manager.get_sound_manager()
            
            print(f"\n当前声音模式: {sound.get_mode()}")
            print(f"声音总开关: {sound.is_enabled()}")
            
            input("\n按 Enter 开始测试向上突破音效...")
            
            # 测试1: 向上突破音效
            print("\n【测试3.1】向上突破音效")
            if config.SOUND_MODE == "synthesized":
                print(f"  配置: {config.UP_ALERT_FREQUENCY}Hz, {config.UP_ALERT_DURATION}秒, {config.UP_ALERT_COUNT}次")
            else:
                print(f"  文件: {config.UP_ALERT_FILE}")
            print("  预期声音: 清脆、短促、两次")
            print("  播放中...")
            
            sound.play_up_alert()
            print("  ✓ 播放完成")
            self.print_result("向上突破音效", True, "请确认听到提示音")
            
            input("\n按 Enter 继续测试向下突破音效...")
            
            # 测试2: 向下突破音效
            print("\n【测试3.2】向下突破音效")
            if config.SOUND_MODE == "synthesized":
                print(f"  配置: {config.DOWN_ALERT_FREQUENCY}Hz, {config.DOWN_ALERT_DURATION}秒, {config.DOWN_ALERT_COUNT}次")
            else:
                print(f"  文件: {config.DOWN_ALERT_FILE}")
            print("  预期声音: 沉闷、长鸣、两次")
            print("  播放中...")
            
            sound.play_down_alert()
            print("  ✓ 播放完成")
            self.print_result("向下突破音效", True, "请确认听到提示音")
            
            input("\n按 Enter 测试系统蜂鸣音...")
            
            # 测试3: 系统蜂鸣音（备用）
            print("\n【测试3.3】系统蜂鸣音")
            print("  预期声音: 电脑内置蜂鸣声")
            print("  播放中...")
            
            try:
                import winsound
                winsound.Beep(1000, 500)
                print("  ✓ 播放完成")
                self.print_result("系统蜂鸣音", True, "请确认听到蜂鸣声")
            except Exception as e:
                print(f"  ⚠ 系统蜂鸣失败: {e}")
                self.print_result("系统蜂鸣音", False, str(e))
            
        except ImportError as e:
            print(f"✗ 模块导入失败: {e}")
            self.print_result("提示音测试", False, "pygame未安装")
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            self.print_result("提示音测试", False, str(e))
        
        self.wait_for_enter()
        return True
    
    # ==================== 测试4: 数据获取测试 ====================
    
    def test_data_fetch(self):
        """测试数据获取功能"""
        self.print_header("测试4: 数据获取功能")
        
        try:
            import akshare as ak
            
            # 测试单个合约
            print(f"\n【测试4.1】单合约测试 - {self.test_symbol}")
            
            start_time = time.time()
            df = ak.futures_zh_minute_sina(symbol=self.test_symbol)
            elapsed_ms = (time.time() - start_time) * 1000
            
            if df is not None and not df.empty:
                latest = float(df['close'].iloc[-1])
                print(f"  ✓ 连接成功")
                print(f"  耗时: {elapsed_ms:.0f}ms")
                print(f"  数据行数: {len(df)}")
                print(f"  最新价: {latest:.2f}")
                print(f"  列名: {list(df.columns)}")
                self.print_result("单合约测试", True, f"最新价 {latest:.2f}")
            else:
                print(f"  ✗ 返回空数据")
                self.print_result("单合约测试", False, "返回空数据")
                return False
            
            # 计算VWAP
            print("\n【测试4.2】VWAP计算测试")
            
            total_turnover = (df['close'] * df['volume']).sum()
            total_volume = df['volume'].sum()
            vwap = total_turnover / total_volume if total_volume > 0 else latest
            
            print(f"  总成交量: {total_volume:,}")
            print(f"  总成交额: {total_turnover:,.0f}")
            print(f"  计算VWAP: {vwap:.2f}")
            print(f"  价格状态: {'高于' if latest > vwap else '低于' if latest < vwap else '等于'}均价")
            print(f"  价差: {latest - vwap:+.2f}")
            
            self.print_result("VWAP计算测试", True, f"VWAP={vwap:.2f}")
            
            # 多合约测试
            print("\n【测试4.3】多合约测试")
            
            success_count = 0
            for symbol in config.SYMBOLS[:5]:
                try:
                    print(f"  正在获取 {symbol}...", end=" ")
                    df2 = ak.futures_zh_minute_sina(symbol=symbol)
                    if df2 is not None and not df2.empty:
                        price = df2['close'].iloc[-1]
                        print(f"✓ {price:.2f}")
                        success_count += 1
                    else:
                        print(f"✗ 无数据")
                    time.sleep(0.3)
                except Exception as e:
                    print(f"✗ {e}")
            
            self.print_result("多合约测试", success_count >= 1, f"成功 {success_count}/{len(config.SYMBOLS)}")
            
        except ImportError as e:
            print(f"✗ akshare未安装: {e}")
            self.print_result("数据获取测试", False, "akshare未安装")
        except Exception as e:
            print(f"✗ 测试失败: {e}")
            self.print_result("数据获取测试", False, str(e))
        
        self.wait_for_enter()
        return True
    
    # ==================== 测试5: 内存监控测试 ====================
    
    def test_memory(self):
        """测试内存监控功能"""
        self.print_header("测试5: 内存监控功能")
        
        try:
            import psutil
            
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            print(f"\n进程信息:")
            print(f"  进程ID: {process.pid}")
            print(f"  进程名称: {process.name()}")
            print(f"  内存使用: {memory_mb:.2f} MB")
            
            print(f"\n系统内存:")
            print(f"  总内存: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB")
            print(f"  可用内存: {psutil.virtual_memory().available / 1024 / 1024:.1f} MB")
            print(f"  使用率: {psutil.virtual_memory().percent}%")
            
            if memory_mb < config.MEMORY_LIMIT_MB:
                print(f"\n✓ 内存使用正常 (低于限制 {config.MEMORY_LIMIT_MB} MB)")
                self.print_result("内存监控", True, f"当前 {memory_mb:.1f} MB")
            else:
                print(f"\n⚠ 内存使用已超限 (高于 {config.MEMORY_LIMIT_MB} MB)")
                self.print_result("内存监控", False, f"超限 {memory_mb:.1f} MB")
            
        except ImportError:
            print("\n✗ psutil未安装")
            print("  请运行: pip install psutil")
            self.print_result("内存监控", False, "psutil未安装")
        except Exception as e:
            print(f"\n✗ 测试失败: {e}")
            self.print_result("内存监控", False, str(e))
        
        self.wait_for_enter()
        return True
    
    # ==================== 测试6: 网络连接测试 ====================
    
    def test_network(self):
        """测试网络连接"""
        self.print_header("测试6: 网络连接测试")
        
        try:
            import requests
            
            # 测试新浪财经
            print("\n【测试6.1】新浪财经连接测试")
            try:
                resp = requests.get("https://hq.sinajs.cn/list=AG2608", timeout=10, 
                                    headers={"Referer": "https://finance.sina.com.cn/"})
                if resp.status_code == 200:
                    content = resp.text
                    if '=""' not in content and content.strip():
                        print(f"  ✓ 连接成功，返回数据")
                        self.print_result("新浪财经连接", True)
                    else:
                        print(f"  ⚠ 连接成功但返回空数据")
                        self.print_result("新浪财经连接", True, "返回空数据（可能非交易时间）")
                else:
                    print(f"  ✗ 连接失败 (状态码: {resp.status_code})")
                    self.print_result("新浪财经连接", False)
            except Exception as e:
                print(f"  ✗ 连接失败: {e}")
                self.print_result("新浪财经连接", False)
            
            # 测试阿里云镜像
            print("\n【测试6.2】阿里云镜像连接测试")
            try:
                resp = requests.get("https://mirrors.aliyun.com/pypi/simple/", timeout=10)
                if resp.status_code == 200:
                    print(f"  ✓ 连接成功")
                    self.print_result("阿里云镜像连接", True)
                else:
                    print(f"  ✗ 连接失败")
                    self.print_result("阿里云镜像连接", False)
            except Exception as e:
                print(f"  ✗ 连接失败: {e}")
                self.print_result("阿里云镜像连接", False)
            
        except ImportError:
            print("\n✗ requests未安装")
            self.print_result("网络测试", False, "requests未安装")
        
        self.wait_for_enter()
        return True
    
    # ==================== 测试7: 自动更新测试 ====================
    
    def test_auto_update(self):
        """测试自动更新功能"""
        self.print_header("测试7: 自动更新功能")
        
        print(f"\nAUTO_UPDATE = {config.AUTO_UPDATE}")
        
        if config.AUTO_UPDATE:
            print("\n自动更新已启用，程序启动时会检查以下模块更新:")
            packages = ["akshare", "pygame-ce", "schedule", "psutil"]
            for pkg in packages:
                print(f"  - {pkg}")
            
            print("\n是否需要手动测试自动更新？")
            print("  1. 是 - 立即尝试更新模块")
            print("  2. 否 - 仅检查配置")
            
            choice = input("\n请输入选择 (1/2): ").strip()
            
            if choice == "1":
                print("\n正在测试更新...")
                try:
                    import subprocess
                    
                    for pkg in packages:
                        print(f"  检查 {pkg}...", end=" ")
                        result = subprocess.run(
                            [sys.executable, "-m", "pip", "install", pkg, "--upgrade",
                             "-i", "https://mirrors.aliyun.com/pypi/simple/",
                             "--trusted-host", "mirrors.aliyun.com",
                             "--disable-pip-version-check"],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        if result.returncode == 0:
                            print("✓")
                        else:
                            print("✗")
                    print("\n更新测试完成")
                except Exception as e:
                    print(f"\n更新测试失败: {e}")
            
            self.print_result("自动更新配置", True, "已启用")
        else:
            print("\n自动更新已禁用，如需启用请修改 config.py 中的 AUTO_UPDATE = True")
            self.print_result("自动更新配置", True, "已禁用（正常）")
        
        self.wait_for_enter()
        return True
    
    # ==================== 测试8: 声音模块独立测试 ====================
    
    def test_sound_module(self):
        """测试声音模块独立功能"""
        self.print_header("测试8: 声音模块独立测试")
        
        try:
            # 初始化声音模块
            sound_manager.init_sound(config)
            sound = sound_manager.get_sound_manager()
            
            print(f"\n声音模块信息:")
            print(f"  pygame可用: {sound_manager.PYGAME_AVAILABLE}")
            print(f"  声音模式: {sound.get_mode()}")
            print(f"  声音总开关: {sound.is_enabled()}")
            
            # 测试配置读取
            print(f"\n配置读取测试:")
            print(f"  UP_ALERT_FREQUENCY: {sound._get_config('UP_ALERT_FREQUENCY', 'N/A')}")
            print(f"  DOWN_ALERT_FREQUENCY: {sound._get_config('DOWN_ALERT_FREQUENCY', 'N/A')}")
            print(f"  ALERT_VOLUME: {sound._get_config('ALERT_VOLUME', 'N/A')}")
            
            self.print_result("声音模块配置", True, "模块工作正常")
            
        except Exception as e:
            print(f"\n✗ 声音模块测试失败: {e}")
            self.print_result("声音模块配置", False, str(e))
        
        self.wait_for_enter()
        return True
    
    # ==================== 运行所有测试 ====================
    
    def run_all_tests(self):
        """运行所有测试"""
        self.clear_screen()
        
        print("\n" + "=" * 60)
        print("期货VWAP监控程序 - 集成测试")
        print("=" * 60)
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"配置文件: config.py")
        print(f"测试合约: {self.test_symbol}")
        
        tests = [
            ("配置文件完整性", self.test_config),
            ("日志记录功能", self.test_logging),
            ("提示音功能", self.test_sound),
            ("数据获取功能", self.test_data_fetch),
            ("内存监控功能", self.test_memory),
            ("网络连接测试", self.test_network),
            ("自动更新功能", self.test_auto_update),
            ("声音模块测试", self.test_sound_module),
        ]
        
        for name, test_func in tests:
            self.clear_screen()
            test_func()
        
        # 打印最终汇总
        self.clear_screen()
        self.print_summary()
    
    def print_summary(self):
        """打印测试汇总"""
        print("\n" + "=" * 60)
        print("测试汇总")
        print("=" * 60)
        
        passed_count = sum(1 for v in self.test_results.values() if v)
        failed_count = len(self.test_results) - passed_count
        
        for name, passed in self.test_results.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {name}")
        
        print("-" * 60)
        print(f"总计: {passed_count} 通过, {failed_count} 失败")
        
        if failed_count == 0:
            print("\n🎉 所有测试通过！程序可以正常运行。")
        else:
            print(f"\n⚠ 有 {failed_count} 项测试失败，请检查：")
            print("  1. 网络连接是否正常")
            print("  2. 音量是否已开启")
            print("  3. 依赖库是否已安装（pip install akshare pygame-ce psutil requests）")
            print("  4. config.py 配置是否正确")
        
        print("\n按 Enter 键退出测试程序...")
        input()


# ==================== 主入口 ====================

def show_menu():
    """显示测试菜单"""
    print("\n" + "=" * 60)
    print("期货VWAP监控程序 - 测试菜单")
    print("=" * 60)
    print("  1. 运行全部测试")
    print("  2. 测试配置文件")
    print("  3. 测试日志记录")
    print("  4. 测试提示音")
    print("  5. 测试数据获取")
    print("  6. 测试内存监控")
    print("  7. 测试网络连接")
    print("  8. 测试自动更新")
    print("  9. 测试声音模块")
    print("  0. 退出")
    print("=" * 60)


if __name__ == "__main__":
    tester = IntegrationTester()
    
    while True:
        show_menu()
        choice = input("请输入选择 (0-9): ").strip()
        
        if choice == "1":
            tester.run_all_tests()
        elif choice == "2":
            tester.test_config()
        elif choice == "3":
            tester.test_logging()
        elif choice == "4":
            tester.test_sound()
        elif choice == "5":
            tester.test_data_fetch()
        elif choice == "6":
            tester.test_memory()
        elif choice == "7":
            tester.test_network()
        elif choice == "8":
            tester.test_auto_update()
        elif choice == "9":
            tester.test_sound_module()
        elif choice == "0":
            print("\n测试程序已退出。")
            break
        else:
            print("\n无效输入，请重新选择。")
            time.sleep(1)