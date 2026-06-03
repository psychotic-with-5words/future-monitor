"""
提示音模块 - 独立的音频管理模块

支持两种声音模式：
1. 合成音效 (synthesized)：使用 pygame 生成指定频率的正弦波
2. 自定义音频文件 (file)：使用用户提供的 WAV 文件

从 config.py 读取配置，不硬编码任何参数
"""

import math
import io
import wave
import struct
import time
import threading
import os
from typing import Optional, Dict, Any

# 尝试导入 pygame
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("警告: pygame 未安装，提示音功能不可用。请运行: pip install pygame-ce")


def create_beep_wav(frequency: int, duration: float, volume: float = 0.5) -> io.BytesIO:
    """
    生成指定频率的 WAV 音频数据（合成音效）
    
    参数:
        frequency: 频率(Hz)
        duration: 时长(秒)
        volume: 音量 (0-1)
    
    返回:
        BytesIO 对象，可直接用于 pygame.mixer.Sound
    """
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    samples = []
    
    # 添加淡入淡出，避免爆音
    fade_samples = int(0.01 * sample_rate)
    
    for i in range(n_samples):
        value = volume * math.sin(2 * math.pi * frequency * i / sample_rate)
        # 淡入
        if i < fade_samples:
            value *= i / fade_samples
        # 淡出
        if i > n_samples - fade_samples:
            value *= (n_samples - i) / fade_samples
        samples.append(int(value * 32767))
    
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(struct.pack('<' + 'h' * n_samples, *samples))
    
    wav_buffer.seek(0)
    return wav_buffer


def load_wav_file(file_path: str) -> Optional[pygame.mixer.Sound]:
    """
    加载 WAV 文件
    
    参数:
        file_path: WAV 文件路径
    
    返回:
        pygame Sound 对象，失败时返回 None
    """
    if not PYGAME_AVAILABLE:
        return None
    
    try:
        if os.path.exists(file_path):
            sound = pygame.mixer.Sound(file_path)
            return sound
        else:
            print(f"警告: 音频文件不存在: {file_path}")
            return None
    except Exception as e:
        print(f"警告: 加载音频文件失败 {file_path}: {e}")
        return None


def play_alert(sound, duration: float, count: int, interval: float):
    """播放提示音（指定次数）"""
    if sound is None:
        return
    
    for i in range(count):
        sound.play()
        if i < count - 1:
            time.sleep(duration + interval)


class SoundManager:
    """声音管理器（单例模式）"""
    
    _instance = None
    _lock = threading.Lock()
    
    # 默认配置
    DEFAULT_CONFIG = {
        "SOUND_ENABLED": True,
        "SOUND_MODE": "synthesized",
        "UP_ALERT_FILE": "sounds/up_alert.wav",
        "DOWN_ALERT_FILE": "sounds/down_alert.wav",
        "UP_ALERT_ENABLED": True,
        "UP_ALERT_FREQUENCY": 1200,
        "UP_ALERT_DURATION": 0.4,
        "UP_ALERT_COUNT": 2,
        "UP_ALERT_INTERVAL": 0.1,
        "DOWN_ALERT_ENABLED": True,
        "DOWN_ALERT_FREQUENCY": 800,
        "DOWN_ALERT_DURATION": 0.7,
        "DOWN_ALERT_COUNT": 2,
        "DOWN_ALERT_INTERVAL": 0.1,
        "ALERT_VOLUME": 0.6,
        "WARMUP_ENABLED": True,
        "WARMUP_FREQUENCY": 500,
        "WARMUP_DURATION": 0.3,
        "WARMUP_VOLUME": 0.3,
    }
    
    def __new__(cls, config_module=None):
        """单例模式：确保只有一个实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_module=None):
        """
        初始化声音管理器
        
        参数:
            config_module: 配置模块（如 import config），如果不传则使用默认值
        """
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        # 保存配置模块引用
        self.cfg = config_module
        
        # 初始化 pygame mixer
        if PYGAME_AVAILABLE:
            pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            self._init_sounds()
        else:
            self.up_sound = None
            self.down_sound = None
    
    def _get_config(self, key, default):
        """从配置模块获取配置值"""
        if self.cfg and hasattr(self.cfg, key):
            return getattr(self.cfg, key)
        return default
    
    def _get_sound_mode(self) -> str:
        """获取声音模式"""
        mode = self._get_config("SOUND_MODE", "synthesized")
        return mode if mode in ["synthesized", "file"] else "synthesized"
    
    def _create_synthesized_sound(self, frequency: int, duration: float, volume: float) -> Optional[pygame.mixer.Sound]:
        """创建合成音效"""
        if not PYGAME_AVAILABLE:
            return None
        
        try:
            return pygame.mixer.Sound(
                create_beep_wav(frequency, duration, volume=volume)
            )
        except Exception as e:
            print(f"警告: 创建合成音效失败: {e}")
            return None
    
    def _load_file_sound(self, file_path: str, default_frequency: int, default_duration: float) -> Optional[pygame.mixer.Sound]:
        """加载音频文件，失败时回退到合成音效"""
        # 尝试加载文件
        sound = load_wav_file(file_path)
        
        if sound is not None:
            return sound
        
        # 回退到合成音效
        volume = self._get_config("ALERT_VOLUME", 0.6)
        print(f"提示: 使用合成音效替代 (频率:{default_frequency}Hz)")
        return self._create_synthesized_sound(default_frequency, default_duration, volume)
    
    def _init_up_sound(self):
        """初始化向上突破音效"""
        mode = self._get_sound_mode()
        volume = self._get_config("ALERT_VOLUME", 0.6)
        
        if mode == "file":
            # 使用自定义音频文件
            file_path = self._get_config("UP_ALERT_FILE", "sounds/up_alert.wav")
            self.up_sound = self._load_file_sound(
                file_path,
                self._get_config("UP_ALERT_FREQUENCY", 1200),
                self._get_config("UP_ALERT_DURATION", 0.4)
            )
            # 记录使用的模式
            if self.up_sound:
                print(f"向上突破音效: 使用文件 {file_path}")
        else:
            # 使用合成音效
            if self._get_config("UP_ALERT_ENABLED", True):
                self.up_sound = self._create_synthesized_sound(
                    self._get_config("UP_ALERT_FREQUENCY", 1200),
                    self._get_config("UP_ALERT_DURATION", 0.4),
                    volume
                )
                print(f"向上突破音效: 使用合成音效 ({self._get_config('UP_ALERT_FREQUENCY', 1200)}Hz)")
            else:
                self.up_sound = None
    
    def _init_down_sound(self):
        """初始化向下突破音效"""
        mode = self._get_sound_mode()
        volume = self._get_config("ALERT_VOLUME", 0.6)
        
        if mode == "file":
            # 使用自定义音频文件
            file_path = self._get_config("DOWN_ALERT_FILE", "sounds/down_alert.wav")
            self.down_sound = self._load_file_sound(
                file_path,
                self._get_config("DOWN_ALERT_FREQUENCY", 800),
                self._get_config("DOWN_ALERT_DURATION", 0.7)
            )
            if self.down_sound:
                print(f"向下突破音效: 使用文件 {file_path}")
        else:
            # 使用合成音效
            if self._get_config("DOWN_ALERT_ENABLED", True):
                self.down_sound = self._create_synthesized_sound(
                    self._get_config("DOWN_ALERT_FREQUENCY", 800),
                    self._get_config("DOWN_ALERT_DURATION", 0.7),
                    volume
                )
                print(f"向下突破音效: 使用合成音效 ({self._get_config('DOWN_ALERT_FREQUENCY', 800)}Hz)")
            else:
                self.down_sound = None
    
    def _init_warmup(self):
        """初始化预热音效"""
        if not self._get_config("WARMUP_ENABLED", True):
            return
        
        warmup_sound = self._create_synthesized_sound(
            self._get_config("WARMUP_FREQUENCY", 500),
            self._get_config("WARMUP_DURATION", 0.3),
            self._get_config("WARMUP_VOLUME", 0.3)
        )
        
        if warmup_sound:
            warmup_sound.play()
            time.sleep(self._get_config("WARMUP_DURATION", 0.3) + 0.1)
    
    def _init_sounds(self):
        """初始化音效对象"""
        # 检查声音总开关
        sound_enabled = self._get_config("SOUND_ENABLED", True)
        if not sound_enabled:
            self.up_sound = None
            self.down_sound = None
            print("声音功能已禁用")
            return
        
        print(f"声音模式: {self._get_sound_mode()}")
        
        # 分别初始化向上和向下音效
        self._init_up_sound()
        self._init_down_sound()
        
        # 预热音效
        self._init_warmup()
    
    def play_up_alert(self):
        """播放向上突破音效"""
        if not PYGAME_AVAILABLE:
            return
        if self.up_sound:
            play_alert(
                self.up_sound,
                self._get_config("UP_ALERT_DURATION", 0.4),
                self._get_config("UP_ALERT_COUNT", 2),
                self._get_config("UP_ALERT_INTERVAL", 0.1)
            )
    
    def play_down_alert(self):
        """播放向下突破音效"""
        if not PYGAME_AVAILABLE:
            return
        if self.down_sound:
            play_alert(
                self.down_sound,
                self._get_config("DOWN_ALERT_DURATION", 0.7),
                self._get_config("DOWN_ALERT_COUNT", 2),
                self._get_config("DOWN_ALERT_INTERVAL", 0.1)
            )
    
    def is_enabled(self) -> bool:
        """检查声音功能是否可用"""
        return PYGAME_AVAILABLE and self._get_config("SOUND_ENABLED", True)
    
    def get_mode(self) -> str:
        """获取当前声音模式"""
        return self._get_sound_mode()
    
    def play_test_sequence(self):
        """播放测试序列"""
        if not self.is_enabled():
            print("声音功能未启用或 pygame 未安装")
            return
        
        print(f"当前声音模式: {self.get_mode()}")
        print("播放测试序列...")
        print("  向上突破音效...")
        self.play_up_alert()
        time.sleep(1)
        print("  向下突破音效...")
        self.play_down_alert()
        print("测试完成")
    
    @classmethod
    def reset_instance(cls):
        """重置单例实例（主要用于测试）"""
        cls._instance = None


# ==================== 便捷函数 ====================

_global_sound_manager = None
_global_config = None


def init_sound(config_module):
    """
    初始化声音模块（必须在使用前调用）
    
    参数:
        config_module: 配置模块（如 import config）
    """
    global _global_sound_manager, _global_config
    _global_config = config_module
    SoundManager.reset_instance()
    _global_sound_manager = SoundManager(config_module)


def get_sound_manager():
    """获取声音管理器实例"""
    global _global_sound_manager
    if _global_sound_manager is None:
        _global_sound_manager = SoundManager(None)
    return _global_sound_manager


def play_up_alert():
    """播放向上突破音效"""
    get_sound_manager().play_up_alert()


def play_down_alert():
    """播放向下突破音效"""
    get_sound_manager().play_down_alert()


def is_sound_enabled() -> bool:
    """检查声音功能是否可用"""
    return get_sound_manager().is_enabled()


def get_sound_mode() -> str:
    """获取当前声音模式"""
    return get_sound_manager().get_mode()


# ==================== 测试入口 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("提示音模块 - 独立测试")
    print("=" * 60)
    
    if not PYGAME_AVAILABLE:
        print("\n请先安装 pygame-ce:")
        print("  pip install pygame-ce")
    else:
        # 尝试导入配置
        try:
            import config
            init_sound(config)
            print("已从 config.py 加载配置")
        except ImportError:
            print("未找到 config.py，使用默认配置")
            init_sound(None)
        
        sound = get_sound_manager()
        
        print(f"\n声音总开关: {sound._get_config('SOUND_ENABLED', True)}")
        print(f"声音模式: {sound.get_mode()}")
        
        print("\n【测试1】向上突破音效")
        input("  按 Enter 播放...")
        sound.play_up_alert()
        
        print("\n【测试2】向下突破音效")
        input("  按 Enter 播放...")
        sound.play_down_alert()
        
        print("\n测试完成！")