#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 VORTEX IP Hunter - Client
Клиент с активацией через сервер и проверкой HWID
"""

import os
import sys
import json
import hashlib
import uuid
import socket
import requests
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
#                         КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════
SERVER_URL = os.getenv("VORTEX_SERVER", "http://YOUR_SERVER:5000")
ACTIVATION_FILE = ".vortex_activation"
CONFIG_CACHE = ".vortex_config"

# ═══════════════════════════════════════════════════════════════
#                      ПОЛУЧЕНИЕ HWID
# ═══════════════════════════════════════════════════════════════
def get_hardware_id() -> str:
    """Получить Hardware ID системы."""
    try:
        # MAC адрес
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                       for elements in range(0,2*6,2)][::-1])
        
        # Hostname
        hostname = socket.gethostname()
        
        # Machine ID (Linux)
        machine_id = ""
        try:
            with open('/etc/machine-id', 'r') as f:
                machine_id = f.read().strip()
        except:
            try:
                with open('/var/lib/dbus/machine-id', 'r') as f:
                    machine_id = f.read().strip()
            except:
                pass
        
        # Комбинируем
        combined = f"{mac}|{hostname}|{machine_id}"
        hw_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        return hw_hash
    except Exception as e:
        print(f"⚠️ Ошибка получения HWID: {e}")
        return "UNKNOWN"


def get_vm_ip() -> str:
    """Получить IP ВМ."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "UNKNOWN"


# ═══════════════════════════════════════════════════════════════
#                         АКТИВАЦИЯ
# ═══════════════════════════════════════════════════════════════
def is_activated() -> bool:
    """Проверка активации."""
    return Path(ACTIVATION_FILE).exists()


def save_activation(activation_code: str):
    """Сохранить код активации."""
    with open(ACTIVATION_FILE, 'w') as f:
        f.write(activation_code)


def load_activation() -> str:
    """Загрузить код активации."""
    try:
        with open(ACTIVATION_FILE, 'r') as f:
            return f.read().strip()
    except:
        return None


def activate():
    """Процесс активации."""
    print("\n" + "="*60)
    print("🔐 АКТИВАЦИЯ VORTEX HUNTER")
    print("="*60 + "\n")
    
    hwid = get_hardware_id()
    vm_ip = get_vm_ip()
    
    print(f"🖥️  Hardware ID: {hwid[:32]}...")
    print(f"🌐 IP ВМ: {vm_ip}\n")
    
    activation_code = input("🔑 Введите код активации из Telegram бота: ").strip().upper()
    
    if not activation_code:
        print("❌ Код активации не может быть пустым")
        return False
    
    print("\n⏳ Отправка запроса на сервер...")
    
    try:
        response = requests.post(
            f"{SERVER_URL}/api/activate",
            json={
                'activation_code': activation_code,
                'hwid': hwid,
                'vm_ip': vm_ip
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ АКТИВАЦИЯ УСПЕШНА!")
            print(f"📱 Telegram ID: {data.get('telegram_id')}")
            print("\n📋 Следующие шаги:")
            print("   1. Вернитесь в Telegram бот")
            print("   2. Настройте аккаунты и подсети")
            print("   3. Запустите охоту командой: vortex-daemon start\n")
            
            save_activation(activation_code)
            return True
        else:
            error = response.json().get('error', 'Unknown error')
            print(f"\n❌ Ошибка активации: {error}")
            return False
    
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Не удалось подключиться к серверу: {SERVER_URL}")
        print("   Проверьте:")
        print("   1. Сервер запущен")
        print("   2. Доступ к серверу по сети")
        print("   3. Правильный VORTEX_SERVER в переменных окружения")
        return False
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
#                      ПОЛУЧЕНИЕ КОНФИГА
# ═══════════════════════════════════════════════════════════════
def fetch_config() -> dict:
    """Получить конфиг с сервера."""
    activation_code = load_activation()
    if not activation_code:
        print("❌ Система не активирована!")
        return None
    
    hwid = get_hardware_id()
    vm_ip = get_vm_ip()
    
    try:
        response = requests.post(
            f"{SERVER_URL}/api/config",
            json={
                'activation_code': activation_code,
                'hwid': hwid,
                'vm_ip': vm_ip
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            config = data.get('config')
            
            # Кэшируем конфиг
            with open(CONFIG_CACHE, 'w') as f:
                json.dump(config, f, indent=2)
            
            return config
        elif response.status_code == 403:
            print("❌ ДОСТУП ЗАПРЕЩЁН!")
            print("   Возможные причины:")
            print("   1. Система переустановлена (изменился HWID)")
            print("   2. ВМ переехала на другой IP")
            print("   3. Лицензия заблокирована")
            print("\n   Свяжитесь с администратором")
            return None
        else:
            error = response.json().get('error', 'Unknown error')
            print(f"❌ Ошибка получения конфига: {error}")
            return None
    
    except requests.exceptions.ConnectionError:
        print("⚠️ Нет связи с сервером, используем кэш...")
        try:
            with open(CONFIG_CACHE, 'r') as f:
                return json.load(f)
        except:
            print("❌ Кэш недоступен!")
            return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None


def verify_access() -> bool:
    """Проверка доступа (heartbeat)."""
    activation_code = load_activation()
    if not activation_code:
        return False
    
    hwid = get_hardware_id()
    vm_ip = get_vm_ip()
    
    try:
        response = requests.post(
            f"{SERVER_URL}/api/heartbeat",
            json={
                'activation_code': activation_code,
                'hwid': hwid,
                'vm_ip': vm_ip
            },
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('valid', False)
        return False
    except:
        # Если сервер недоступен, разрешаем работу (офлайн режим)
        return True


# ═══════════════════════════════════════════════════════════════
#                         ГЛАВНАЯ ЛОГИКА
# ═══════════════════════════════════════════════════════════════
def main():
    print("\n🎯 VORTEX IP Hunter Pro v5.0\n")
    
    # Проверка активации
    if not is_activated():
        print("⚠️ Система не активирована\n")
        if not activate():
            sys.exit(1)
    
    # Проверка доступа
    print("🔍 Проверка доступа...")
    if not verify_access():
        print("❌ ДОСТУП ЗАПРЕЩЁН!")
        print("   Свяжитесь с администратором")
        sys.exit(1)
    
    print("✅ Доступ разрешён\n")
    
    # Получение конфига
    print("📥 Загрузка конфигурации с сервера...")
    config = fetch_config()
    
    if not config:
        print("❌ Не удалось получить конфиг")
        sys.exit(1)
    
    # Проверка наличия аккаунтов
    accounts = config.get('accounts', [])
    subnets = config.get('subnets', [])
    
    print(f"\n✅ Конфигурация загружена:")
    print(f"   👥 Аккаунтов: {len(accounts)}")
    print(f"   🎯 Подсетей: {len(subnets)}\n")
    
    if not accounts:
        print("⚠️ Нет настроенных аккаунтов!")
        print("   Настройте через Telegram бот")
        sys.exit(1)
    
    if not subnets:
        print("⚠️ Нет настроенных подсетей!")
        print("   Настройте через Telegram бот")
        sys.exit(1)
    
    # ЗДЕСЬ НАЧИНАЕТСЯ ОСНОВНАЯ ЛОГИКА ОХОТЫ
    print("="*60)
    print("🚀 ЗАПУСК ОХОТЫ")
    print("="*60)
    print("\n⚠️ ЭТО ДЕМО - основная логика из hunter_pro.py будет здесь\n")
    
    # TODO: Интегрировать логику из hunter_pro.py
    # Hunter(config).run()


if __name__ == "__main__":
    main()
