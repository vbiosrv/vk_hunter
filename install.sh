#!/bin/bash
#
# VORTEX IP Hunter - Установщик клиента
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

INSTALL_DIR="/opt/vortex"
REPO_URL="https://github.com/YOUR_USERNAME/vortex-hunter.git"
COMMAND_NAME="vortex"
SERVER_URL="${VORTEX_SERVER:-http://YOUR_SERVER:5000}"

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║        🎯 VORTEX IP Hunter - Установщик                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Проверка root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Запустите с правами root (sudo)${NC}"
    exit 1
fi

# Установка зависимостей
echo -e "${YELLOW}📦 Установка зависимостей...${NC}"
if command -v apt-get &> /dev/null; then
    apt-get update -qq
    apt-get install -y python3 python3-pip python3-venv git curl
fi

# Удаление старой версии
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}🗑️  Удаление старой версии...${NC}"
    rm -rf "$INSTALL_DIR"
fi

# Клонирование
echo -e "${YELLOW}📥 Скачивание...${NC}"
if [ -n "$GITHUB_TOKEN" ]; then
    REPO_WITH_TOKEN=$(echo $REPO_URL | sed "s|https://|https://$GITHUB_TOKEN@|")
    git clone --depth 1 "$REPO_WITH_TOKEN" "$INSTALL_DIR" 2>/dev/null
else
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"
fi

# Виртуальное окружение
echo -e "${YELLOW}🐍 Создание venv...${NC}"
python3 -m venv "$INSTALL_DIR/venv"

# Установка библиотек
echo -e "${YELLOW}📦 Установка библиотек...${NC}"
"$INSTALL_DIR/venv/bin/pip" install --quiet requests openstacksdk python-dotenv colorama

# Создание команды
cat > /usr/local/bin/$COMMAND_NAME << SCRIPT
#!/bin/bash
cd /opt/vortex
export VORTEX_SERVER="$SERVER_URL"
./venv/bin/python vortex_client.py "\$@"
SCRIPT

chmod +x /usr/local/bin/$COMMAND_NAME
chmod +x "$INSTALL_DIR/vortex_client.py"

mkdir -p "$INSTALL_DIR/logs"

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    ✅ УСТАНОВКА ЗАВЕРШЕНА!                    ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}🔐 АКТИВАЦИЯ${NC}"
echo ""
echo -e "1. Откройте Telegram бота: ${CYAN}@YOUR_BOT_NAME${NC}"
echo -e "2. Отправьте ${CYAN}/start${NC} и получите код активации"
echo -e "3. Запустите на ВМ: ${CYAN}vortex${NC}"
echo -e "4. Введите код активации"
echo -e "5. Настройте аккаунты через бота"
echo ""
echo -e "${CYAN}Сервер: ${SERVER_URL}${NC}"
echo ""
