#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 VORTEX IP Hunter - Клиент v5.0
Активация через ключи + охота
"""

import os
import sys
import time
import json
import random
import sqlite3
import logging
import hashlib
import uuid
import socket
import requests
from datetime import datetime
from pathlib import Path

# Константы
VERSION = "5.0"
SERVER_URL = os.getenv("VORTEX_SERVER", "http://45.144.52.209:5000")
ACTIVATION_FILE = ".vortex_activation"
CONFIG_CACHE = ".vortex_config.json"
DB_FILE = "vortex_hunt.db"
LOG_DIR = "logs"
RUNNING_FLAG = ".vortex_running"

# Цвета
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    NC = '\033[0m'

def print_color(text, color):
    print(f"{color}{text}{Colors.NC}")

# ============================================================
#                    АКТИВАЦИЯ
# ============================================================
def get_hardware_id():
    """HWID"""
    try:
        with open('/etc/machine-id') as f:
            machine_id = f.read().strip()
    except:
        machine_id = str(uuid.uuid4())
    
    hwid = hashlib.sha256(f"{machine_id}{socket.gethostname()}".encode()).hexdigest()
    return hwid

def get_vm_ip():
    """Внешний IP"""
    try:
        return requests.get('http://api.ipify.org', timeout=5).text
    except:
        return "0.0.0.0"

def is_activated():
    return Path(ACTIVATION_FILE).exists()

def save_activation(key):
    with open(ACTIVATION_FILE, 'w') as f:
        f.write(key)

def load_activation():
    try:
        with open(ACTIVATION_FILE) as f:
            return f.read().strip()
    except:
        return None

def activate():
    """Активация"""
    print("\n" + "="*50)
    print_color("🔐 АКТИВАЦИЯ", Colors.CYAN)
    print("="*50)
    
    hwid = get_hardware_id()
    vm_ip = get_vm_ip()
    
    print(f"HWID: {hwid[:16]}...")
    print(f"IP: {vm_ip}\n")
    
    key = input("🔑 Введите ключ: ").strip().upper()
    
    if not key:
        print_color("❌ Код не может быть пустым", Colors.RED)
        return False
    
    try:
        r = requests.post(
            f"{SERVER_URL}/api/activate",
            json={'activation_key': key, 'hwid': hwid, 'vm_ip': vm_ip},
            timeout=10
        )
        
        if r.status_code == 200:
            print_color("\n✅ АКТИВАЦИЯ УСПЕШНА!", Colors.GREEN)
            save_activation(key)
            return True
        else:
            print_color(f"\n❌ Ошибка: {r.json().get('error', 'Unknown')}", Colors.RED)
            return False
            
    except Exception as e:
        print_color(f"\n❌ Ошибка: {e}", Colors.RED)
        return False

def verify_access():
    """Проверка доступа"""
    key = load_activation()
    if not key:
        return False
    
    try:
        r = requests.post(
            f"{SERVER_URL}/api/heartbeat",
            json={'activation_key': key, 'hwid': get_hardware_id(), 'vm_ip': get_vm_ip()},
            timeout=5
        )
        return r.status_code == 200 and r.json().get('valid', False)
    except:
        return True

# ============================================================
#                      БАЗА ДАННЫХ
# ============================================================
class DB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.execute('''CREATE TABLE IF NOT EXISTS captures (
            id INTEGER PRIMARY KEY, account TEXT, ip TEXT, subnet TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        self.conn.commit()
    
    def log_capture(self, account, ip, subnet):
        self.conn.execute('INSERT INTO captures (account, ip, subnet) VALUES (?, ?, ?)',
                         (account, ip, subnet))
        self.conn.commit()
    
    def get_stats(self):
        return self.conn.execute('SELECT account, COUNT(*) FROM captures GROUP BY account').fetchall()
    
    def get_recent(self, limit=10):
        return self.conn.execute(
            'SELECT * FROM captures ORDER BY timestamp DESC LIMIT ?', (limit,)
        ).fetchall()

# ============================================================
#                      ЛОГИРОВАНИЕ
# ============================================================
def setup_logging():
    Path(LOG_DIR).mkdir(exist_ok=True)
    log_file = Path(LOG_DIR) / f"hunt_{datetime.now():%Y%m%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================
#                      КОМАНДЫ
# ============================================================
def cmd_activate():
    if is_activated():
        print_color("✅ Уже активировано", Colors.GREEN)
        return
    activate()

def cmd_start():
    if not is_activated():
        print_color("❌ Сначала выполните: vortex activate", Colors.RED)
        return
    
    if Path(RUNNING_FLAG).exists():
        print_color("⚠️ Охота уже запущена", Colors.YELLOW)
        return
    
    if not verify_access():
        print_color("❌ Доступ запрещен", Colors.RED)
        return
    
    Path(RUNNING_FLAG).touch()
    print_color("✅ Охота запущена", Colors.GREEN)
    
    # Здесь будет логика охоты

def cmd_stop():
    if not Path(RUNNING_FLAG).exists():
        print_color("⚠️ Охота не запущена", Colors.YELLOW)
        return
    
    Path(RUNNING_FLAG).unlink(missing_ok=True)
    print_color("✅ Остановлено", Colors.GREEN)

def cmd_status():
    print("\n" + "="*50)
    print_color("📊 СТАТУС", Colors.CYAN)
    print("="*50)
    
    if is_activated():
        print_color("✅ Активировано", Colors.GREEN)
        key = load_activation()
        if key:
            print(f"Ключ: {key[:8]}...{key[-8:]}")
    else:
        print_color("❌ Не активировано", Colors.RED)
    
    if verify_access():
        print_color("✅ Доступ к серверу есть", Colors.GREEN)
    else:
        print_color("⚠️ Офлайн режим", Colors.YELLOW)
    
    if Path(RUNNING_FLAG).exists():
        print_color("\n🟢 Охота: РАБОТАЕТ", Colors.GREEN)
    else:
        print_color("\n🔴 Охота: ОСТАНОВЛЕНА", Colors.YELLOW)
    
    db = DB()
    stats = db.get_stats()
    if stats:
        print("\n📈 Статистика:")
        for acc, cnt in stats:
            print(f"   {acc}: {cnt}")
    
    recent = db.get_recent(3)
    if recent:
        print("\n📝 Последние:")
        for r in recent:
            print(f"   {r[2]} ({r[4]})")
    
    print()

def main():
    if len(sys.argv) < 2:
        print(f"VORTEX IP Hunter v{VERSION}")
        print("\nКоманды:")
        print("  vortex activate   - Активация")
        print("  vortex start      - Запуск")
        print("  vortex stop       - Остановка")
        print("  vortex status     - Статус")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "activate":
        cmd_activate()
    elif cmd in ["start", "hunt"]:
        cmd_start()
    elif cmd == "stop":
        cmd_stop()
    elif cmd == "status":
        cmd_status()
    else:
        print_color(f"❌ Неизвестная команда: {cmd}", Colors.RED)

if __name__ == "__main__":
    main()
