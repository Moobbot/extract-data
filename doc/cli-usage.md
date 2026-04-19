# CLI usage

## Chay nhanh

```bash
python simple_extractor.py path/to/image.png --agent gemini
python simple_extractor.py path/to/image.png --agent openai --model gpt-4o
python simple_extractor.py path/to/image.png --agent openai_compatible --base-url http://127.0.0.1:1234/v1 --api-key local --model qwen2.5-vl
python simple_extractor.py path/to/image.png --agent local_http --base-url http://127.0.0.1:8080/ocr
```

## Output format

```bash
python simple_extractor.py path/to/image.png --format markdown
python simple_extractor.py path/to/image.png --format json
```

Khi chay voi `--format json`, script se luu JSON va thu xuat them Excel `.xlsx` neu parse du lieu thanh cong.

## Tham so chinh

- `--agent`: ten agent (`gemini`, `openai`, `openai_compatible`, `local_http`, hoac env agent)
- `--model`: override model
- `--base-url`: endpoint cho openai-compatible/local_http
- `--api-key`: override api key
- `--provider`: alias tuong thich nguoc cua `--agent`
