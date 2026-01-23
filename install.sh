#!/bin/bash
#
# VORTEX IP Hunter - Client Installer (FINAL)
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="/opt/vortex"
REPO_URL="https://github.com/Mastachok/VORTEX_HUNTER.git"
SERVER_URL="${VORTEX_SERVER:-http://178.250.247.165:5000}"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║        🎯 VORTEX IP Hunter - Установщик                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Установка зависимостей
echo -e "${YELLOW}📦 Установка зависимостей...${NC}"
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git curl

# Удаление старой версии
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}🗑️  Удаление старой версии...${NC}"
    rm -rf "$INSTALL_DIR"
fi

# Клонирование
echo -e "${YELLOW}📥 Скачивание с GitHub...${NC}"
if [ -n "$GITHUB_TOKEN" ]; then
    REPO_WITH_TOKEN=$(echo $REPO_URL | sed "s|https://|https://$GITHUB_TOKEN@|")
    git clone --depth 1 "$REPO_WITH_TOKEN" "$INSTALL_DIR" 2>/dev/null || {
        echo -e "${RED}❌ Не удалось скачать репозиторий${NC}"
        echo -e "${YELLOW}Попробуйте без токена или проверьте доступ${NC}"
        exit 1
    }
else
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR" || {
        echo -e "${RED}❌ Не удалось скачать репозиторий${NC}"
        echo -e "${YELLOW}Репозиторий должен быть публичным или используйте GITHUB_TOKEN${NC}"
        exit 1
    }
fi

cd "$INSTALL_DIR"

# Виртуальное окружение
echo -e "${YELLOW}🐍 Создание venv...${NC}"
python3 -m venv venv

# Установка библиотек
echo -e "${YELLOW}📦 Установка библиотек...${NC}"
./venv/bin/pip install --quiet --upgrade pip
./venv/bin/pip install --quiet requests openstacksdk

# Создание команды vortex
cat > /usr/local/bin/vortex << SCRIPT
#!/bin/bash
cd $INSTALL_DIR
export VORTEX_SERVER="$SERVER_URL"
$INSTALL_DIR/venv/bin/python vortex_client.py "\$@"
SCRIPT

chmod +x /usr/local/bin/vortex
chmod +x "$INSTALL_DIR/vortex_client.py"

# Создание директорий
mkdir -p "$INSTALL_DIR/logs"

# Создание systemd сервиса
cat > /etc/systemd/system/vortex-hunt.service << EOF
[Unit]
Description=VORTEX IP Hunter
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
Environment="VORTEX_SERVER=$SERVER_URL"
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/vortex_client.py start
Restart=on-failure
RestartSec=30

StandardOutput=append:$INSTALL_DIR/logs/hunt.log
StandardError=append:$INSTALL_DIR/logs/hunt_error.log

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ УСТАНОВКА ЗАВЕРШЕНА!                    ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}🔐 АКТИВАЦИЯ${NC}"
echo -e "   ${YELLOW}vortex activate${NC}      - Активация через Telegram бот"
echo -e "   Получите код активации в боте: ${CYAN}@vortex_hunter_bot${NC}"
echo ""
echo -e "${CYAN}🎯 КОМАНДЫ${NC}"
echo -e "   ${YELLOW}vortex start${NC}         - Запустить охоту"
echo -e "   ${YELLOW}vortex stop${NC}          - Остановить охоту"
echo -e "   ${YELLOW}vortex status${NC}        - Статус системы"
echo ""
echo -e "${CYAN}🔧 SYSTEMD (фоновый режим)${NC}"
echo -e "   ${YELLOW}systemctl start vortex-hunt${NC}    - Запуск в фоне"
echo -e "   ${YELLOW}systemctl status vortex-hunt${NC}   - Статус"
echo -e "   ${YELLOW}systemctl enable vortex-hunt${NC}   - Автозапуск"
echo ""
echo -e "${CYAN}📊 Сервер: ${GREEN}$SERVER_URL${NC}"
echo ""
echo -e "${YELLOW}📋 Следующие шаги:${NC}"
echo -e "   1. Получите код в Telegram боте"
echo -e "   2. Выполните: ${CYAN}vortex activate${NC}"
echo -e "   3. Настройте аккаунты через бота"
echo -e "   4. Запустите: ${CYAN}vortex start${NC}"
echo ""
