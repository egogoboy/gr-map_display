#!/usr/bin/env bash
set -e

echo "[INFO] Checking system dependencies..."

# Проверка на apt
if ! command -v apt &> /dev/null; then
    echo "[ERROR] This script requires apt-based system (Ubuntu/Debian)."
    exit 1
fi

# Обновляем пакеты
sudo apt update

# Список необходимых пакетов
DEPS="cmake make g++ python3 python3-venv python3-pip gnuradio gnuradio-dev python3-pyqt5 python3-pyqt5.qtsvg python3-pyqt5.qtwebsockets"

for pkg in $DEPS; do
    if dpkg -s $pkg &> /dev/null; then
        echo "[OK] $pkg is already installed"
    else
        echo "[INFO] Installing $pkg..."
        sudo apt install -y $pkg
    fi
done

echo "[INFO] System dependencies installed."

# Python окружение
if [ ! -d "env" ]; then
    echo "[INFO] Creating Python virtual environment..."
    python3 -m venv env
fi

echo "[INFO] Activating virtual environment..."
source env/bin/activate

echo "[INFO] Installing Python requirements..."
pip install --upgrade pip
pip install -r requirements.txt

# Сборка
echo "[INFO] Building project..."
mkdir -p build
cd build
cmake ..
make -j$(nproc)

echo "[INFO] Installing project..."
sudo make install

echo "[SUCCESS] Installation completed!"
