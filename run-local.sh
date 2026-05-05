#!/usr/bin/env bash
set -euo pipefail

SERVICE="app"
ENV_NAME="extract-pdf"
DEVICE_MODE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        app|lightonocr|both)
            SERVICE="$1"
            shift
            ;;
        --device)
            DEVICE_MODE="${2:-}"
            shift 2
            ;;
        --cpu)
            DEVICE_MODE="cpu"
            shift
            ;;
        --gpu)
            DEVICE_MODE="gpu"
            shift
            ;;
        --name)
            ENV_NAME="${2:-}"
            shift 2
            ;;
        *)
            echo "[ERROR] Tham so khong hop le: $1"
            echo "Dung: bash run-local.sh [app|lightonocr|both] [--name <env>] [--cpu|--gpu|--device cpu|gpu|auto]"
            exit 1
            ;;
    esac
done

if [[ -n "$DEVICE_MODE" && "$DEVICE_MODE" != "cpu" && "$DEVICE_MODE" != "gpu" && "$DEVICE_MODE" != "cuda" && "$DEVICE_MODE" != "auto" ]]; then
    echo "[ERROR] DEVICE khong hop le: $DEVICE_MODE"
    echo "Dung: --device cpu|gpu|cuda|auto"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if env exists
if ! conda env list | awk '{print $1}' | grep -Fxq "$ENV_NAME"; then
    echo "[ERROR] Env '$ENV_NAME' khong ton tai."
    echo "Chay setup-all.sh truoc de tao env."
    exit 1
fi

echo ""
echo "==============================================="
echo "  Extract-PDF + LightOnOCR Local Runner"
echo "  ENV_NAME = $ENV_NAME"
echo "  SERVICE  = $SERVICE"
if [[ -n "$DEVICE_MODE" ]]; then
    echo "  DEVICE   = $DEVICE_MODE"
fi
echo "==============================================="
echo ""

LIGHTONOCR_ENV=()
if [[ -n "$DEVICE_MODE" ]]; then
    LIGHTONOCR_ENV=("LIGHTONOCR_DEVICE=$DEVICE_MODE")
fi

case "$SERVICE" in
    app)
        echo "> Chay extract-pdf app server (port 8000)"
        echo ""
        conda run -n "$ENV_NAME" python -m app.main
        ;;
    lightonocr)
        echo "> Chay LightOnOCR API server (port 7861)"
        echo ""
        cd LightOnOCR-2-1B
        env "${LIGHTONOCR_ENV[@]}" conda run -n "$ENV_NAME" python api.py
        ;;
    both)
        echo "> Chay extract-pdf + LightOnOCR cung luc"
        echo "  - extract-pdf:  http://localhost:8000/ui"
        echo "  - LightOnOCR:   http://localhost:7861/"
        echo ""
        
        # Start extract-pdf in background
        echo "Khoi dong extract-pdf..."
        conda run -n "$ENV_NAME" python -m app.main &
        APP_PID=$!
        
        sleep 2
        
        # Start LightOnOCR in foreground
        echo "Khoi dong LightOnOCR..."
        cd LightOnOCR-2-1B
        trap "kill $APP_PID 2>/dev/null || true" EXIT
        env "${LIGHTONOCR_ENV[@]}" conda run -n "$ENV_NAME" python api.py
        ;;
    *)
        echo "Dung: bash run-local.sh [app|lightonocr|both] [--name <env>] [--cpu|--gpu|--device cpu|gpu|auto]"
        read -p "Press Enter to exit"
        exit 1
        ;;
esac

read -p "Press Enter to exit"
