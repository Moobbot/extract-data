# API va agent

## API chinh

- `GET /api/v1/agents`
- `POST /api/v1/extract`
- `POST /api/v1/extract/batch`
- `POST /api/v1/extract/folder`
- `POST /api/v1/extract/json`
- `GET /api/v1/task-status/{task_id}`
- `GET /api/v1/task-artifact/{task_id}/json`
- `GET /api/v1/task-artifact/{task_id}/excel`

## JSON schema cho /extract/json

```json
{
  "image_path": null,
  "image_base64": "<base64-image>",
  "filename": "sample.jpg",
  "agent": "gemini",
  "output_format": "markdown",
  "save_to_file": false,
  "options": {
    "model": null,
    "base_url": null,
    "api_key": null
  }
}
```

Neu `save_to_file=true` va `output_format=json`, worker se luu ca `*.json` va `*.xlsx` trong `outputs/`.

## Cach chon agent

### Gemini

- Dat `agent = gemini` hoac bo trong de dung mac dinh.

### OpenAI

- Dat `agent = openai`.
- Co the override `options.model`.

### OpenAI-compatible

- Dat `agent = openai_compatible`.
- Bat buoc co `options.base_url`, `options.api_key`, `options.model`.

### Local HTTP (generic)

- Dat `agent = local_http`.
- Bat buoc co `options.base_url`.
- `options.api_key` la tuy chon.

Adapter gui payload:

- `image_base64`
- `prompt`

Parser uu tien field: `content`, `text`, `result`, `markdown`, `output`.

## Goi LightOnOCR (he ben ngoai)

- Chay LightOnOCR trong env/doc vu rieng.
- Trong `extract-pdf`, goi bang `agent = local_http`.
- Set `options.base_url` toi endpoint OCR cua LightOnOCR.