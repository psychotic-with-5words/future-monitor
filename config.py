"""
配置文件 - 期货VWAP监控程序
修改此文件即可调整程序行为，无需改动主程序
"""

# ==================== 监控配置 ====================
# 要监控的期货合约列表
SYMBOLS = ["AG2608", "CU2607", "FU2609"]

# 检查间隔（秒）- 完成所有合约检查后到下一次开始的等待时间
CHECK_INTERVAL = 5

# 合约间延迟（秒）- 同一轮检查中两个合约之间的等待时间
BATCH_DELAY = 0.3

# 数据获取失败时的最大重试次数
MAX_RETRIES = 3

# 重试等待时间（秒）- 每次重试会翻倍
RETRY_DELAY = 2

# 价格容忍度 - 价格与均价差异小于此值时视为"等于均价"
TOLERANCE = 0.5

# ==================== 重启配置 ====================
# 定时重启时间（24小时制）
RESTART_TIMES = ["05:00", "17:00"]

# ==================== 内存监控配置 ====================
# 内存超过此值（MB）时自动重启
MEMORY_LIMIT_MB = 500

# 垃圾回收间隔（秒）
GC_INTERVAL = 60

# ==================== 更新配置 ====================
# 启动时是否自动更新模块
AUTO_UPDATE = True

# ==================== 日志配置 ====================
# 日志文件夹名称
LOG_DIR = "logs"

# 日志文件名
LOG_FILE = "vwap_monitor.log"

# 日志级别: 10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR
LOG_LEVEL = 20  # 20 = INFO

# 单个日志文件最大大小（字节）
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB

# 保留的日志文件备份数量
LOG_BACKUP_COUNT = 30

# 是否输出到控制台
LOG_CONSOLE_OUTPUT = True

# ==================== 声音配置 ====================
# 声音功能总开关
SOUND_ENABLED = True

# ----- 声音模式选择 -----
# 声音模式: "synthesized" (合成音效) 或 "file" (自定义音频文件)
SOUND_MODE = "synthesized"

# ----- 自定义音频文件路径（当 SOUND_MODE = "file" 时使用）-----
# 支持格式: WAV 文件
# 如果文件不存在，自动回退到合成音效
UP_ALERT_FILE = "sounds/up_alert.wav"      # 向上突破提示音文件
DOWN_ALERT_FILE = "sounds/down_alert.wav"  # 向下突破提示音文件

# ----- 向上突破音效（低于均价 → 高于均价）-----
# 仅在 SOUND_MODE = "synthesized" 时生效
UP_ALERT_ENABLED = True          # 是否启用
UP_ALERT_FREQUENCY = 1200        # 频率（Hz）- 高频清脆
UP_ALERT_DURATION = 0.4          # 单次时长（秒）
UP_ALERT_COUNT = 2               # 播放次数
UP_ALERT_INTERVAL = 0.1          # 次数间隔（秒）

# ----- 向下突破音效（高于均价 → 低于均价）-----
# 仅在 SOUND_MODE = "synthesized" 时生效
DOWN_ALERT_ENABLED = True        # 是否启用
DOWN_ALERT_FREQUENCY = 800       # 频率（Hz）- 低频沉闷
DOWN_ALERT_DURATION = 0.7        # 单次时长（秒）
DOWN_ALERT_COUNT = 2             # 播放次数
DOWN_ALERT_INTERVAL = 0.1        # 次数间隔（秒）

# ----- 全局音量 -----
# 音量 (0-1)，对所有音效生效（对自定义音频文件可能无效，取决于文件本身的音量）
ALERT_VOLUME = 0.6

# ----- 预热音效（程序启动时激活音频设备）-----
WARMUP_ENABLED = True            # 是否启用
WARMUP_FREQUENCY = 500           # 频率（Hz）
WARMUP_DURATION = 0.3            # 时长（秒）
WARMUP_VOLUME = 0.3              # 音量 (0-1)

# ==================== 开机自启动配置 ====================
# 是否启用开机自启动（True=启用，False=禁用）
ENABLE_STARTUP = True

# 开机自启动标识（用于 autostarter）
STARTUP_IDENTIFIER = "futures_vwap_monitor"
