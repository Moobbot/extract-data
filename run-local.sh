#!/usr/bin/env bash
set -euo pipefail

SERVICE="app"
ENV_NAME="extract-pdf"

while [[ $# -gt 0 ]]; do
    case "$1" in
        app|lightonocr|both)
            SERVICE="$1"
            shift
            ;;
        --name)
            ENV_NAME="${2:-}"
            shift 2
            ;;
        *)
            echo "[ERROR] Tham so khong hop le: $1"
            echo "Dung: bash run-local.sh [app|lightonocr|both] [--name <env>]"
            exit 1
            ;;
    esac
done

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
echo "==============================================="
echo ""

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
        conda run -n "$ENV_NAME" python api.py
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
        conda run -n "$ENV_NAME" python api.py
        ;;
    *)
        echo "Dung: bash run-local.sh [app|lightonocr|both] [--name <env>]"
        exit 1
        ;;
esac
