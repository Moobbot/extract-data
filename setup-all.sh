#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="extract-pdf"
PYTHON_VERSION="3.10"
DEVICE_MODE="gpu"
FORCE_RECREATE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --name)
            ENV_NAME="${2:-}"
            shift 2
            ;;
        --python)
            PYTHON_VERSION="${2:-}"
            shift 2
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
        --force-recreate)
            FORCE_RECREATE=true
            shift
            ;;
        *)
            echo "[ERROR] Tham so khong hop le: $1"
            echo "Dung: bash setup-all.sh [--name <env>] [--python <version>] [--device cpu|gpu] [--force-recreate]"
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_SCRIPT="$SCRIPT_DIR/build-conda.sh"
LIGHT_DIR="$SCRIPT_DIR/LightOnOCR-2-1B"
LIGHT_SETUP="$LIGHT_DIR/setup_env.sh"

if [[ ! -f "$BUILD_SCRIPT" ]]; then
    echo "[ERROR] Khong tim thay script: $BUILD_SCRIPT"
    exit 1
fi

if [[ ! -f "$LIGHT_SETUP" ]]; then
    echo "[ERROR] Khong tim thay script: $LIGHT_SETUP"
    exit 1
fi

echo ""
echo "==============================================="
echo "  Setup tong extract-pdf + LightOnOCR-2-1B"
echo "  ENV_NAME       = $ENV_NAME"
echo "  PYTHON_VERSION = $PYTHON_VERSION"
echo "  DEVICE_MODE    = $DEVICE_MODE"
echo "  FORCE_RECREATE = $FORCE_RECREATE"
echo "==============================================="
echo ""

# Step 1: Build/update env cho extract-pdf
BUILD_ARGS=("--name" "$ENV_NAME" "--python" "$PYTHON_VERSION")
if [[ "$FORCE_RECREATE" == true ]]; then
    BUILD_ARGS+=("--force-recreate")
fi

echo "> Step 1/2: Build conda env cho extract-pdf"
bash "$BUILD_SCRIPT" "${BUILD_ARGS[@]}"
if [[ $? -ne 0 ]]; then
    echo "[ERROR] Build env extract-pdf that bai."
    exit 1
fi

# Step 2: Cai setup LightOnOCR trong cung env
echo ""
echo "> Step 2/2: Setup LightOnOCR-2-1B"
cd "$LIGHT_DIR"

LIGHT_ARGS=("--name" "$ENV_NAME" "--python" "$PYTHON_VERSION" "--$DEVICE_MODE")
bash "$LIGHT_SETUP" "${LIGHT_ARGS[@]}"
if [[ $? -ne 0 ]]; then
    echo "[ERROR] Setup LightOnOCR that bai."
    exit 1
fi

cd "$SCRIPT_DIR"

echo ""
echo "Hoan tat setup tong."
echo "Kich hoat env: conda activate $ENV_NAME"
echo "Chay extract-pdf: python -m app.main"
echo "Chay LightOnOCR API:"
echo "  cd LightOnOCR-2-1B"
echo "  python api.py"
echo ""
read -p "Press Enter to exit"
