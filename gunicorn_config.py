"""
Gunicorn 生产环境配置
使用方式：gunicorn -c gunicorn_config.py app:create_app --preload
"""
import os

# === 绑定 ===
bind = "127.0.0.1:5000"

# === Worker 进程 ===
# 根据 CPU 核数设置：2 * CPU_CORE + 1，限制在 2~4 范围内
_cpu_count = os.cpu_count() or 2
workers = min(max(2, 2 * _cpu_count + 1), 4)
worker_class = "sync"          # 默认同步 worker，无需额外依赖
worker_connections = 1000      # 每个 worker 最大并发连接
timeout = 30                   # 请求超时（秒）
keepalive = 2                  # 长连接保持时间（秒）
preload_app = True             # 预加载应用（配合 create_app 工厂模式）

# === 日志 ===
base_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(base_dir, "logs")
os.makedirs(log_dir, exist_ok=True)

accesslog = os.path.join(log_dir, "access.log")
errorlog = os.path.join(log_dir, "error.log")
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# === 进程管理 ===
daemon = False                 # 由 systemd 托管，不后台化
pidfile = os.path.join(log_dir, "gunicorn.pid")
