# Cau hinh

## Env extract-pdf

```env
GOOGLE_API_KEY=your_google_key
OPENAI_API_KEY=your_openai_key
AI_PROVIDER=gemini
OPENAI_MODEL=gpt-4o
GEMINI_MODEL=gemini-2.5-flash
OPENAI_BASE_URL=
LOCAL_HTTP_TIMEOUT=60
CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-web-app.com
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Cau hinh CORS cho web ngoai

- Them domain frontend vao `CORS_ALLOW_ORIGINS` (tach boi dau phay).
- Sau khi doi `.env`, restart API server.

Vi du:

```env
CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-web-app.com
```

## Agent tuy bien bang env

```env
AGENT_QWEN_TYPE=openai_compatible
AGENT_QWEN_BASE_URL=http://127.0.0.1:1234/v1
AGENT_QWEN_API_KEY=local
AGENT_QWEN_MODEL=qwen2.5-vl
```

Khi goi API, dung `agent = qwen`.

## UI config JSON

- File cau hinh UI: `ui-config.json` o root repository.
- Trang settings: `http://127.0.0.1:8000/ui/settings`.
- Preset mac dinh: `LightOnOCR-2-1B` qua `local_http` voi `base_url = http://127.0.0.1:7860/ocr`.
- Neu doi preset, UI se luu lai vao file JSON va trang trich xuat se nap lai preset do luc mo trang.
