#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 VORTEX IP Hunter - Production Client v5.0
Полный клиент с охотой + активация через сервер
"""

import os, sys, time, json, random, sqlite3, logging, hashlib, uuid, socket, requests, ipaddress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict

# Кодировка
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'

try:
    from openstack import connection
    from openstack import exceptions as os_exc
    OPENSTACK_AVAILABLE = True
except ImportError:
    OPENSTACK_AVAILABLE = False

# Константы
VERSION = "5.0"
SERVER_URL = os.getenv("VORTEX_SERVER", "http://YOUR_SERVER:5000")
ACTIVATION_FILE = ".vortex_activation"
CONFIG_CACHE = ".vortex_config.json"
DB_FILE = "vortex_hunt.db"
LOG_DIR = "logs"
RUNNING_FLAG = ".vortex_running"

class C:
    RST, R, G, Y, C, B = "\033[0m", "\033[91m", "\033[92m", "\033[93m", "\033[96m", "\033[94m"

def clr(t, c): return f"{c}{t}{C.RST}"

# ═══════════════════════════════════════════════════════════════
#                    АКТИВАЦИЯ И HWID
# ═══════════════════════════════════════════════════════════════
def get_hardware_id():
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> e) & 0xff) for e in range(0,12,2)][::-1])
        hostname = socket.gethostname()
        machine_id = ""
        try:
            with open('/etc/machine-id') as f: machine_id = f.read().strip()
        except: pass
        return hashlib.sha256(f"{mac}|{hostname}|{machine_id}".encode()).hexdigest()
    except: return "UNKNOWN"

def get_vm_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "UNKNOWN"

def is_activated():
    return Path(ACTIVATION_FILE).exists()

def save_activation(code):
    with open(ACTIVATION_FILE, 'w') as f: f.write(code)

def load_activation():
    try:
        with open(ACTIVATION_FILE) as f: return f.read().strip()
    except: return None

def activate():
    print("\n" + "="*60)
    print(clr("🔐 АКТИВАЦИЯ VORTEX HUNTER", C.Y))
    print("="*60)
    hwid, vm_ip = get_hardware_id(), get_vm_ip()
    print(f"🖥️  Hardware ID: {hwid[:32]}...\n🌐 IP ВМ: {vm_ip}\n")
    code = input("🔑 Введите код активации из Telegram: ").strip().upper()
    if not code:
        print(clr("❌ Код не может быть пустым", C.R))
        return False
    print("\n⏳ Отправка запроса...")
    try:
        r = requests.post(f"{SERVER_URL}/api/activate", json={'activation_code': code, 'hwid': hwid, 'vm_ip': vm_ip}, timeout=10)
        if r.status_code == 200:
            print(clr("\n✅ АКТИВАЦИЯ УСПЕШНА!", C.G))
            print("📋 Настройте аккаунты через Telegram бот и запустите: vortex hunt\n")
            save_activation(code)
            return True
        else:
            print(clr(f"\n❌ Ошибка: {r.json().get('error', 'Unknown')}", C.R))
            return False
    except requests.exceptions.ConnectionError:
        print(clr(f"\n❌ Не удалось подключиться к серверу: {SERVER_URL}", C.R))
        return False
    except Exception as e:
        print(clr(f"\n❌ Ошибка: {e}", C.R))
        return False

def fetch_config():
    code = load_activation()
    if not code: return None
    try:
        r = requests.post(f"{SERVER_URL}/api/config", json={'activation_code': code, 'hwid': get_hardware_id(), 'vm_ip': get_vm_ip()}, timeout=10)
        if r.status_code == 200:
            cfg = r.json()['config']
            with open(CONFIG_CACHE, 'w') as f: json.dump(cfg, f)
            return cfg
        elif r.status_code == 403:
            print(clr("❌ ДОСТУП ЗАПРЕЩЁН! Свяжитесь с администратором", C.R))
            return None
        else:
            print(clr(f"❌ Ошибка получения конфига: {r.json().get('error')}", C.R))
            return None
    except:
        try:
            with open(CONFIG_CACHE) as f: return json.load(f)
        except:
            print(clr("❌ Кэш недоступен!", C.R))
            return None

def verify_access():
    code = load_activation()
    if not code: return False
    try:
        r = requests.post(f"{SERVER_URL}/api/heartbeat", json={'activation_code': code, 'hwid': get_hardware_id(), 'vm_ip': get_vm_ip()}, timeout=5)
        return r.status_code == 200 and r.json().get('valid', False)
    except: return True  # Офлайн режим

# ═══════════════════════════════════════════════════════════════
#                      БАЗА ДАННЫХ
# ═══════════════════════════════════════════════════════════════
class DB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self._init_db()
    
    def _init_db(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS captures (
            id INTEGER PRIMARY KEY, account TEXT, ip TEXT, subnet TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        self.conn.commit()
    
    def log_capture(self, account, ip, subnet):
        self.conn.execute('INSERT INTO captures (account, ip, subnet) VALUES (?, ?, ?)', (account, ip, subnet))
        self.conn.commit()
    
    def get_stats(self):
        c = self.conn.execute('SELECT account, COUNT(*) as cnt FROM captures GROUP BY account')
        return c.fetchall()
    
    def get_recent(self, limit=10):
        c = self.conn.execute('SELECT * FROM captures ORDER BY timestamp DESC LIMIT ?', (limit,))
        return c.fetchall()

# ═══════════════════════════════════════════════════════════════
#                      ЛОГИРОВАНИЕ
# ═══════════════════════════════════════════════════════════════
def setup_logging():
    Path(LOG_DIR).mkdir(exist_ok=True)
    log_file = Path(LOG_DIR) / f"hunt_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s',
                       handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
    return logging.getLogger(__name__)

logger = setup_logging()

# ═══════════════════════════════════════════════════════════════
#                      ЛОГИКА ОХОТЫ
# ═══════════════════════════════════════════════════════════════
@dataclass
class Account:
    name: str
    username: str
    password: str
    project_id: str
    server_id: str
    project_domain: str = "users"
    auth_url: str = "https://infra.mail.ru:35357/v3/"
    region: str = "RegionOne"
    enabled: bool = True
    
    def get_connection(self):
        return connection.Connection(
            auth_url=self.auth_url, project_id=self.project_id, username=self.username,
            password=self.password, user_domain_name="users", project_domain_name=self.project_domain,
            region_name=self.region, identity_api_version="3", compute_api_version="2"
        )

class Hunter:
    def __init__(self, config):
        self.config = config
        self.accounts = [Account(**acc) for acc in config['accounts'] if acc['enabled']]
        self.subnets = [ipaddress.ip_network(s) for s in config['subnets']]
        self.db = DB()
        self.stop_flag = False
    
    def check_ip_in_subnets(self, ip_str):
        try:
            ip = ipaddress.ip_address(ip_str)
            return any(ip in subnet for subnet in self.subnets)
        except: return False
    
    def hunt_account(self, account: Account):
        logger.info(f"🎯 [{account.name}] Начало охоты")
        try:
            conn = account.get_connection()
            server = conn.compute.get_server(account.server_id)
            if not server:
                logger.error(f"❌ [{account.name}] Сервер не найден")
                return
            
            # Получаем внутренний порт
            internal_port = None
            for net_name, addresses in server.addresses.items():
                for addr in addresses:
                    if addr.get('OS-EXT-IPS:type') == 'fixed':
                        ports = list(conn.network.ports(fixed_ips=f"ip_address={addr['addr']}"))
                        if ports: internal_port = ports[0].id
                        break
                if internal_port: break
            
            if not internal_port:
                logger.error(f"❌ [{account.name}] Внутренний порт не найден")
                return
            
            iteration = 0
            while not self.stop_flag:
                iteration += 1
                logger.info(f"🔄 [{account.name}] Итерация #{iteration}")
                
                # Список FIP
                existing_fips = list(conn.network.ips(project_id=account.project_id))
                logger.info(f"📊 [{account.name}] FIP: {len(existing_fips)}")
                
                # Проверка существующих
                for fip in existing_fips:
                    if self.check_ip_in_subnets(fip.floating_ip_address):
                        logger.info(clr(f"✅ [{account.name}] НАЙДЕН: {fip.floating_ip_address}", C.G))
                        self.db.log_capture(account.name, fip.floating_ip_address, str(self.subnets[0]))
                        return  # Успех!
                
                # Создание нового FIP
                try:
                    new_fip = conn.network.create_ip(floating_network_id="ext-net")
                    ip_addr = new_fip.floating_ip_address
                    logger.info(f"🆕 [{account.name}] Новый FIP: {ip_addr}")
                    
                    if self.check_ip_in_subnets(ip_addr):
                        # НАЙДЕН!
                        logger.info(clr(f"🎉 [{account.name}] ЗАХВАТ! {ip_addr}", C.G))
                        try:
                            conn.network.update_ip(new_fip, port_id=internal_port)
                            logger.info(clr(f"✅ [{account.name}] Привязан к серверу!", C.G))
                            self.db.log_capture(account.name, ip_addr, str(self.subnets[0]))
                            return  # Успех!
                        except Exception as e:
                            logger.error(f"❌ [{account.name}] Ошибка привязки: {e}")
                    else:
                        # Не наш, удаляем
                        conn.network.delete_ip(new_fip)
                        logger.info(f"🗑️ [{account.name}] Удалён: {ip_addr}")
                    
                    # Задержка
                    delay = random.uniform(0.5, 2.0)
                    time.sleep(delay)
                
                except os_exc.ConflictException:
                    logger.warning(f"⚠️ [{account.name}] Лимит FIP достигнут")
                    time.sleep(5)
                except Exception as e:
                    logger.error(f"❌ [{account.name}] Ошибка: {e}")
                    time.sleep(3)
        
        except Exception as e:
            logger.error(f"❌ [{account.name}] Критическая ошибка: {e}")
    
    def run(self):
        logger.info("🚀 ЗАПУСК ОХОТЫ")
        logger.info(f"👥 Аккаунтов: {len(self.accounts)}")
        logger.info(f"🎯 Подсетей: {len(self.subnets)}")
        
        # Создаём флаг что охота запущена
        Path(RUNNING_FLAG).touch()
        
        try:
            import threading
            threads = []
            for acc in self.accounts:
                t = threading.Thread(target=self.hunt_account, args=(acc,))
                t.start()
                threads.append(t)
            
            for t in threads:
                t.join()
        finally:
            Path(RUNNING_FLAG).unlink(missing_ok=True)
        
        logger.info("✅ Охота завершена")

# ═══════════════════════════════════════════════════════════════
#                      КОМАНДЫ
# ═══════════════════════════════════════════════════════════════
def cmd_start():
    """Запуск охоты"""
    if not is_activated():
        print(clr("❌ Система не активирована! Запустите: vortex activate", C.R))
        return
    
    if Path(RUNNING_FLAG).exists():
        print(clr("⚠️ Охота уже запущена!", C.Y))
        return
    
    print("🔍 Проверка доступа...")
    if not verify_access():
        print(clr("❌ ДОСТУП ЗАПРЕЩЁН!", C.R))
        return
    
    print("📥 Загрузка конфигурации...")
    config = fetch_config()
    if not config:
        print(clr("❌ Не удалось получить конфиг", C.R))
        return
    
    accounts = [a for a in config['accounts'] if a['enabled']]
    subnets = config['subnets']
    
    print(f"\n✅ Конфигурация загружена:")
    print(f"   👥 Аккаунтов: {len(accounts)}")
    print(f"   🎯 Подсетей: {len(subnets)}\n")
    
    if not accounts:
        print(clr("⚠️ Нет активных аккаунтов!", C.Y))
        return
    
    if not subnets:
        print(clr("⚠️ Нет подсетей!", C.Y))
        return
    
    if not OPENSTACK_AVAILABLE:
        print(clr("❌ openstacksdk не установлен!", C.R))
        return
    
    print("="*60)
    print(clr("🚀 ЗАПУСК ОХОТЫ", C.G))
    print("="*60)
    
    hunter = Hunter(config)
    hunter.run()

def cmd_stop():
    """Остановка охоты"""
    if not Path(RUNNING_FLAG).exists():
        print(clr("⚠️ Охота не запущена", C.Y))
        return
    
    Path(RUNNING_FLAG).unlink(missing_ok=True)
    print(clr("✅ Сигнал остановки отправлен", C.G))

def cmd_status():
    """Статус охоты"""
    print("\n" + "="*60)
    print(clr("📊 СТАТУС VORTEX HUNTER", C.C))
    print("="*60)
    
    # Активация
    if is_activated():
        print(clr("✅ Система активирована", C.G))
    else:
        print(clr("❌ Не активирована", C.R))
        return
    
    # Охота
    if Path(RUNNING_FLAG).exists():
        print(clr("🟢 Охота: РАБОТАЕТ", C.G))
    else:
        print(clr("🔴 Охота: ОСТАНОВЛЕНА", C.Y))
    
    # Конфиг
    config = fetch_config()
    if config:
        accounts = [a for a in config['accounts'] if a['enabled']]
        print(f"👥 Аккаунтов: {len(accounts)}")
        print(f"🎯 Подсетей: {len(config['subnets'])}")
    
    # Статистика
    db = DB()
    stats = db.get_stats()
    if stats:
        print("\n📈 Статистика захватов:")
        for acc, cnt in stats:
            print(f"   {acc}: {cnt}")
    
    recent = db.get_recent(5)
    if recent:
        print("\n📝 Последние захваты:")
        for r in recent:
            print(f"   {r[1]} - {r[2]} ({r[4]})")
    
    print()

def cmd_activate():
    """Активация системы"""
    if is_activated():
        print(clr("✅ Система уже активирована", C.G))
        print("Для повторной активации удалите файл .vortex_activation")
        return
    activate()

# ═══════════════════════════════════════════════════════════════
#                      ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════════
def main():
    print(f"\n🎯 VORTEX IP Hunter Pro v{VERSION}\n")
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("   vortex activate   - Активация системы")
        print("   vortex start      - Запуск охоты")
        print("   vortex stop       - Остановка охоты")
        print("   vortex status     - Статус системы")
        print("   vortex hunt       - То же что start (алиас)")
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
        print(clr(f"❌ Неизвестная команда: {cmd}", C.R))
        sys.exit(1)

if __name__ == "__main__":
    main()
