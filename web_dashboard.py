"""
Web 操作面板 - 期货VWAP监控程序
提供实时行情看板、配置管理、穿越记录查询等功能
"""

import threading
import time
import json  # 添加
import os    # 添加
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import eventlet

# 导入监控模块
import config
import logger_config
import sound_manager
import akshare as ak

# ==================== Flask 配置 ====================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'vwap_monitor_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# ==================== 全局状态 ====================
# 运行时配置（可动态修改）
runtime_config = {
    "check_interval": config.CHECK_INTERVAL,
    "batch_delay": config.BATCH_DELAY,
    "tolerance": config.TOLERANCE,
    "symbols": config.SYMBOLS.copy()
}
# 最新行情数据
market_data = {}
# 穿越记录列表
cross_records = []
# 运行状态
running_status = {
    "is_running": True,
    "start_time": datetime.now(),
    "loop_count": 0,
    "last_update": None
}

# ==================== 配置保存/加载 ====================
def save_config_to_file():
    """保存配置到文件"""
    config_data = {
        "SYMBOLS": runtime_config["symbols"],
        "CHECK_INTERVAL": runtime_config["check_interval"],
        "BATCH_DELAY": runtime_config["batch_delay"],
        "TOLERANCE": runtime_config["tolerance"],
    }
    try:
        with open("config_runtime.json", "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存配置失败: {e}")
        return False


def load_config_from_file():
    """从文件加载配置"""
    global runtime_config
    try:
        if os.path.exists("config_runtime.json"):
            with open("config_runtime.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                runtime_config["symbols"] = data.get("SYMBOLS", runtime_config["symbols"])
                runtime_config["check_interval"] = data.get("CHECK_INTERVAL", runtime_config["check_interval"])
                runtime_config["batch_delay"] = data.get("BATCH_DELAY", runtime_config["batch_delay"])
                runtime_config["tolerance"] = data.get("TOLERANCE", runtime_config["tolerance"])
            print("已加载保存的配置")
            return True
    except Exception as e:
        print(f"加载配置失败: {e}")
    return False

# ==================== 数据获取线程 ====================
class DataFetcher:
    """后台数据获取线程"""
    
    def __init__(self):
        self.running = True
        self.symbols = runtime_config["symbols"]
        self.interval = runtime_config["check_interval"]
        self.batch_delay = runtime_config["batch_delay"]
        self.status_map = {symbol: None for symbol in self.symbols}
        self.cross_count = {symbol: 0 for symbol in self.symbols}
    
    def update_config(self):
        """更新配置（动态调整）"""
        self.symbols = runtime_config["symbols"]
        self.interval = runtime_config["check_interval"]
        self.batch_delay = runtime_config["batch_delay"]
        # 重置状态映射
        for symbol in self.symbols:
            if symbol not in self.status_map:
                self.status_map[symbol] = None
                self.cross_count[symbol] = 0
    
    def get_realtime_data(self, symbol):
        """获取单个合约数据"""
        try:
            df = ak.futures_zh_minute_sina(symbol=symbol)
            if df is not None and not df.empty:
                latest = float(df['close'].iloc[-1])
                total_turnover = (df['close'] * df['volume']).sum()
                total_volume = df['volume'].sum()
                vwap = total_turnover / total_volume if total_volume > 0 else latest
                return latest, vwap
        except Exception as e:
            pass
        return None, None
    
    def check_status_change(self, symbol, price, vwap):
        """检查状态变化"""
        tolerance = runtime_config["tolerance"]  # 使用运行时配置
        if price > vwap + tolerance:
            current = "above"
        elif price < vwap - tolerance:
            current = "below"
        else:
            current = "equal"
        
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
    
    def run(self):
        """主循环"""
        while self.running:
            loop_start = datetime.now()
            
            for symbol in self.symbols:
                price, vwap = self.get_realtime_data(symbol)
                
                if price is not None and vwap is not None:
                    # 保存数据
                    market_data[symbol] = {
                        "price": price,
                        "vwap": vwap,
                        "spread": price - vwap,
                        "spread_percent": (price - vwap) / vwap * 100 if vwap != 0 else 0,
                        "last_update": datetime.now().strftime("%H:%M:%S"),
                        "status": "above" if price > vwap else "below"
                    }
                    
                    # 检查穿越
                    changed, direction = self.check_status_change(symbol, price, vwap)
                    if changed and direction:
                        record = {
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "symbol": symbol,
                            "direction": direction,
                            "price": price,
                            "vwap": vwap,
                            "spread": price - vwap,
                            "count": self.cross_count[symbol]
                        }
                        cross_records.insert(0, record)
                        # 只保留最近100条记录
                        while len(cross_records) > 100:
                            cross_records.pop()
                        
                        # 通过 WebSocket 推送穿越告警
                        socketio.emit('cross_alert', record)
                    
                    # 通过 WebSocket 推送实时数据
                    socketio.emit('market_update', {
                        "symbol": symbol,
                        "price": price,
                        "vwap": vwap,
                        "spread": price - vwap,
                        "status": "above" if price > vwap else "below"
                    })
                else:
                    market_data[symbol] = {
                        "price": None,
                        "vwap": None,
                        "spread": None,
                        "last_update": datetime.now().strftime("%H:%M:%S"),
                        "status": "error"
                    }
                
                time.sleep(self.batch_delay)
            
            # 更新运行状态
            running_status["last_update"] = datetime.now()
            running_status["loop_count"] += 1
            
            # 计算等待时间
            elapsed = (datetime.now() - loop_start).total_seconds()
            wait_time = max(0, self.interval - elapsed)
            if wait_time > 0:
                time.sleep(wait_time)


# 启动数据获取线程
fetcher = DataFetcher()
data_thread = None


# ==================== Web 路由 ====================

@app.route('/')
def index():
    return render_template('dashboard.html', config=config, market_data=market_data)


@app.route('/api/market_data')
def api_market_data():
    """获取实时行情数据"""
    return jsonify({
        "data": market_data,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": running_status
    })


@app.route('/api/cross_records')
def api_cross_records():
    """获取穿越记录"""
    limit = request.args.get('limit', 50, type=int)
    return jsonify(cross_records[:limit])


@app.route('/api/config')
def api_config():
    """获取当前配置（包括运行时配置）"""
    return jsonify({
        "symbols": runtime_config["symbols"],
        "check_interval": runtime_config["check_interval"],
        "batch_delay": runtime_config["batch_delay"],
        "tolerance": runtime_config["tolerance"],
        "original_symbols": config.SYMBOLS,
        "restart_times": config.RESTART_TIMES,
        "memory_limit_mb": config.MEMORY_LIMIT_MB,
        "sound_enabled": config.SOUND_ENABLED,
        "sound_mode": config.SOUND_MODE,
        "auto_update": config.AUTO_UPDATE,
        "enable_startup": getattr(config, 'ENABLE_STARTUP', True)
    })


@app.route('/api/config/save', methods=['POST'])
def api_save_config():
    """保存配置"""
    global runtime_config, fetcher
    try:
        data = request.get_json()
        
        # 更新运行时配置
        if 'symbols' in data:
            runtime_config["symbols"] = data['symbols']
        if 'check_interval' in data:
            runtime_config["check_interval"] = int(data['check_interval'])
        if 'batch_delay' in data:
            runtime_config["batch_delay"] = float(data['batch_delay'])
        if 'tolerance' in data:
            runtime_config["tolerance"] = float(data['tolerance'])
        
        # 保存到文件
        save_config_to_file()
        
        # 更新数据获取线程的配置
        fetcher.update_config()
        
        # 通知前端配置已更新
        socketio.emit('config_updated', runtime_config)
        
        return jsonify({"success": True, "config": runtime_config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/config/reset', methods=['POST'])
def api_reset_config():
    """重置配置到原始值"""
    global runtime_config, fetcher
    runtime_config["symbols"] = config.SYMBOLS.copy()
    runtime_config["check_interval"] = config.CHECK_INTERVAL
    runtime_config["batch_delay"] = config.BATCH_DELAY
    runtime_config["tolerance"] = config.TOLERANCE
    
    fetcher.update_config()
    save_config_to_file()
    socketio.emit('config_updated', runtime_config)
    
    return jsonify({"success": True, "config": runtime_config})


@app.route('/api/status')
def api_status():
    """获取运行状态"""
    return jsonify({
        "is_running": running_status["is_running"],
        "start_time": running_status["start_time"].strftime("%Y-%m-%d %H:%M:%S"),
        "loop_count": running_status["loop_count"],
        "last_update": running_status["last_update"].strftime("%H:%M:%S") if running_status["last_update"] else None
    })


@app.route('/api/health')
def api_health():
    """健康检查"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@socketio.on('connect')
def handle_connect():
    """客户端连接时发送当前数据"""
    print(f"客户端已连接")
    for symbol, data in market_data.items():
        if data.get("price"):
            emit('market_update', {
                "symbol": symbol,
                "price": data["price"],
                "vwap": data["vwap"],
                "spread": data["spread"],
                "status": data["status"]
            })
    for record in cross_records[:10]:
        emit('cross_alert', record)


def start_web_server():
    """启动 Web 服务器"""
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False)


def start_data_fetcher():
    """启动数据获取线程"""
    global data_thread
    data_thread = threading.Thread(target=fetcher.run, daemon=True)
    data_thread.start()


# ==================== 主入口 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("期货 VWAP 监控程序 - Web 操作面板")
    print("=" * 60)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"监控合约: {', '.join(runtime_config['symbols'])}")
    print(f"检查间隔: {runtime_config['check_interval']} 秒")
    print("=" * 60)
    print("\nWeb 面板地址: http://localhost:5000")
    print("按 Ctrl+C 停止服务\n")
    
    # 加载保存的配置
    load_config_from_file()
    fetcher.update_config()
    
    # 启动数据获取线程
    start_data_fetcher()
    
    # 启动 Web 服务器
    try:
        start_web_server()
    except KeyboardInterrupt:
        print("\n正在停止...")
        fetcher.running = False
        if data_thread:
            data_thread.join(timeout=3)
        print("服务已停止")