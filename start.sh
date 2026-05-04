#!/usr/bin/env bash
# start.sh — Tự động chọn CPU/GPU dựa trên LIGHTONOCR_DEVICE trong .env
#
# Cách dùng:
#   ./start.sh              — khởi động (tự detect, GPU là mặc định)
#   ./start.sh down         — dừng tất cả services
#   ./start.sh logs         — xem logs
#   ./start.sh --build      — rebuild image trước khi start
#
# Logic:
#   LIGHTONOCR_DEVICE=cpu  → docker-compose.cpu.yml (không cần nvidia)
#   LIGHTONOCR_DEVICE=*    → docker-compose.yml     (mặc định GPU)

set -euo pipefail

COMMAND="${1:-up}"
BUILD=false
for arg in "$@"; do
    [[ "$arg" == "--build" || "$arg" == "-build" ]] && BUILD=true
done

# ── Đọc LIGHTONOCR_DEVICE từ .env ──────────────────────────────────────────
DEVICE="auto"
if [[ -f ".env" ]]; then
    line=$(grep -E '^\s*LIGHTONOCR_DEVICE\s*=' .env | tail -1 || true)
    if [[ -n "$line" ]]; then
        DEVICE=$(echo "$line" | cut -d'=' -f2 | tr -d '"' | tr -d "'" | xargs | tr '[:upper:]' '[:lower:]')
    fi
fi

echo ""
echo "=================================================="
echo "  Extract-PDF + LightOnOCR Startup"
echo "  LIGHTONOCR_DEVICE = $DEVICE"
echo "=================================================="

# ── Chọn compose file theo device ───────────────────────────────────────────
if [[ "$DEVICE" == "cpu" ]]; then
    COMPOSE_FILE="docker-compose.cpu.yml"
    echo "  Mode: CPU  (file: docker-compose.cpu.yml)"
    echo "  RAM:  Cần ≥ 12 GB RAM cho Docker"
else
    COMPOSE_FILE="docker-compose.yml"
    echo "  Mode: GPU  (file: docker-compose.yml)"
    echo "  Yêu cầu: nvidia-container-toolkit"
fi
echo "=================================================="
echo ""

BASE_ARGS=("-f" "$COMPOSE_FILE" "--profile" "lightonocr")

case "$COMMAND" in
    up)
        UP_ARGS=("${BASE_ARGS[@]}" "up" "-d")
        [[ "$BUILD" == true ]] && UP_ARGS+=("--build")
        echo "Chạy: docker compose ${UP_ARGS[*]}"
        echo ""
        docker compose "${UP_ARGS[@]}"
        ;;
    down)
        docker compose "${BASE_ARGS[@]}" down
        ;;
    logs)
        docker compose "${BASE_ARGS[@]}" logs -f
        ;;
    restart)
        docker compose "${BASE_ARGS[@]}" restart
        ;;
    ps)
        docker compose "${BASE_ARGS[@]}" ps
        ;;
    *)
        echo "Dùng: ./start.sh [up|down|logs|restart|ps] [--build]"
        exit 1
        ;;
esac
