#!/bin/bash
# Arranque rápido del SCADA
set -e

COMPOSE="$HOME/.local/bin/docker-compose"

# Comprobar docker-compose
if ! command -v docker-compose &>/dev/null && ! [ -f "$COMPOSE" ]; then
  echo "Instalando docker-compose..."
  mkdir -p "$HOME/.local/bin"
  curl -fsSL "https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64" \
    -o "$COMPOSE"
  chmod +x "$COMPOSE"
fi

[ -f "$COMPOSE" ] && COMPOSE="$COMPOSE" || COMPOSE="docker-compose"

# Crear .env si no existe
if [ ! -f .env ]; then
  echo "Creando .env desde .env.example..."
  cp .env.example .env
  echo "REVISA el fichero .env antes de continuar en producción."
fi

echo ""
echo "Arrancando SCADA..."
$COMPOSE up --build -d

echo ""
echo "========================================"
echo "  SCADA arrancado correctamente"
echo "  Dashboard: http://localhost:3000"
echo "  API:       http://localhost:8000/docs"
echo "========================================"
