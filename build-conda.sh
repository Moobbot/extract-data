#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="extract-pdf"
PYTHON_VERSION="3.10"
WITH_LIGHTONOCR=false
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
        --with-lightonocr)
            WITH_LIGHTONOCR=true
            shift
            ;;
        --force-recreate)
            FORCE_RECREATE=true
            shift
            ;;
        *)
            echo "Tham so khong hop le: $1"
            echo "Dung: ./build-conda.sh [--name <env_name>] [--python <version>] [--with-lightonocr] [--force-recreate]"
            exit 1
            ;;
    esac
done

if ! command -v conda >/dev/null 2>&1; then
    echo "Khong tim thay lenh 'conda'. Hay cai Anaconda/Miniconda truoc."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "==============================================="
echo "  Build local Conda env for extract-pdf"
echo "  ENV_NAME        = $ENV_NAME"
echo "  PYTHON_VERSION  = $PYTHON_VERSION"
echo "  WITH_LIGHTONOCR = $WITH_LIGHTONOCR"
echo "==============================================="
echo ""

if [[ "$FORCE_RECREATE" == true ]]; then
    if conda env list | awk '{print $1}' | grep -Fxq "$ENV_NAME"; then
        echo "> Xoa env cu: $ENV_NAME"
        conda env remove -n "$ENV_NAME" -y
    fi
fi

if conda env list | awk '{print $1}' | grep -Fxq "$ENV_NAME"; then
    echo "> Env da ton tai: $ENV_NAME"
else
    echo "> Tao env moi: $ENV_NAME (python=$PYTHON_VERSION)"
    conda create -n "$ENV_NAME" -y "python=$PYTHON_VERSION" pip
fi

echo "> Cai dependencies chinh tu requirements.txt"
conda run -n "$ENV_NAME" python -m pip install --upgrade pip
conda run -n "$ENV_NAME" python -m pip install -r requirements.txt

if [[ "$WITH_LIGHTONOCR" == true ]]; then
    LIGHT_REQ="$SCRIPT_DIR/LightOnOCR-2-1B/requirements.txt"
    if [[ -f "$LIGHT_REQ" ]]; then
        echo "> Cai them dependencies LightOnOCR"
        conda run -n "$ENV_NAME" python -m pip install -r "$LIGHT_REQ"
    else
        echo "> Khong tim thay $LIGHT_REQ, bo qua"
    fi
fi

echo ""
echo "Hoan tat."
echo "Kich hoat env: conda activate $ENV_NAME"
echo "Chay app:      python -m app.main"
echo ""
