#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="/opt/vortex"
SERVER_URL="${VORTEX_SERVER:-http://45.144.52.209:5000}"

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════╗"
echo "║        🎯 VORTEX IP Hunter - Установщик           ║"
echo "╚════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Зависимости
echo -e "${YELLOW}📦 Установка зависимостей...${NC}"
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv git curl

# Создание директории
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Скачивание клиента
echo -e "${YELLOW}📥 Скачивание клиента...${NC}"
curl -sL "https://raw.githubusercontent.com/vbiosrv/vk_hunter/main/client/vortex_client.py" -o vortex_client.py

# Виртуальное окружение
echo -e "${YELLOW}🐍 Создание venv...${NC}"
python3 -m venv venv
./venv/bin/pip install --quiet --upgrade pip
./venv/bin/pip install --quiet requests

# Команда vortex
cat > /usr/local/bin/vortex << EOF
#!/bin/bash
cd $INSTALL_DIR
export VORTEX_SERVER="$SERVER_URL"
$INSTALL_DIR/venv/bin/python vortex_client.py "\$@"
EOF

chmod +x /usr/local/bin/vortex
chmod +x vortex_client.py

# Директории
mkdir -p logs

echo ""
echo -e "${GREEN}✅ УСТАНОВКА ЗАВЕРШЕНА!${NC}"
echo ""
echo -e "${CYAN}🔐 Активация:${NC}  vortex activate"
echo -e "${CYAN}🚀 Запуск:${NC}     vortex start"
echo -e "${CYAN}📊 Статус:${NC}     vortex status"
echo -e "${CYAN}🛑 Остановка:${NC}  vortex stop"
echo ""
