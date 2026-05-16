#!/bin/bash
# SCADA Web Industrial — mifsut.com
# Instalación y arranque en un solo comando:
#   bash <(curl -fsSL https://raw.githubusercontent.com/joseluisnebot/mifsut-scada/main/start.sh)
set -e

REPO="https://github.com/joseluisnebot/mifsut-scada.git"
DIR="$HOME/scada"
COMPOSE="$HOME/.local/bin/docker-compose"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   SCADA Web Industrial — mifsut.com      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Docker ────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "► Instalando Docker..."
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
  echo "  Docker instalado. Es posible que necesites cerrar sesión"
  echo "  y volver a entrar para que el grupo docker se aplique."
  echo "  Si el arranque falla por permisos, ejecuta: newgrp docker"
else
  echo "✓ Docker encontrado: $(docker --version)"
fi

# ── 2. docker-compose ────────────────────────────────────────────────────────
if ! command -v docker-compose &>/dev/null && ! [ -f "$COMPOSE" ]; then
  echo "► Instalando docker-compose..."
  mkdir -p "$HOME/.local/bin"
  curl -fsSL "https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64" \
    -o "$COMPOSE"
  chmod +x "$COMPOSE"
  echo "✓ docker-compose instalado"
else
  echo "✓ docker-compose encontrado"
fi

[ -f "$COMPOSE" ] && COMPOSE="$COMPOSE" || COMPOSE="docker-compose"

# ── 3. git ───────────────────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
  echo "► Instalando git..."
  sudo apt-get update -qq && sudo apt-get install -y -qq git
fi

# ── 4. Clonar o actualizar ───────────────────────────────────────────────────
if [ -d "$DIR/.git" ]; then
  echo "► Actualizando repositorio existente en $DIR..."
  git -C "$DIR" pull
else
  echo "► Clonando repositorio en $DIR..."
  git clone "$REPO" "$DIR"
fi

cd "$DIR"

# ── 5. .env ──────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✓ Fichero .env creado desde .env.example"
fi

# ── 6. Arrancar ──────────────────────────────────────────────────────────────
echo ""
echo "► Construyendo y arrancando servicios (primera vez puede tardar 5-10 min)..."
echo ""
$COMPOSE up --build -d

# ── 7. Resultado ─────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   ✓  SCADA arrancado correctamente       ║"
echo "╠══════════════════════════════════════════╣"
echo "║   Dashboard:  http://localhost:3000       ║"
echo "║   API docs:   http://localhost:8000/docs  ║"
echo "╠══════════════════════════════════════════╣"
echo "║   Modo simulador activo (MOCK_DEVICES)    ║"
echo "║   Ver GUIA_USUARIO.md para producción     ║"
echo "╚══════════════════════════════════════════╝"
echo ""
