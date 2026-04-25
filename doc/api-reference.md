# API va agent

## API chinh

- `GET /api/v1/agents`
- `GET /api/v1/ui-config`
- `PUT /api/v1/ui-config`
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
- Neu muon chon model theo preset UI, `local_http` se gui them field `model` trong payload body.

## Huong dan setup API Agent cho nguoi dung

Muc tieu: nguoi dung co the tu chon agent khi goi API ma khong can sua code backend.

### Buoc 1: Chuan bi env

Them cac bien can thiet vao `.env`:

```env
# Agent mac dinh
AI_PROVIDER=gemini

# Built-in keys
GOOGLE_API_KEY=your_google_key
OPENAI_API_KEY=your_openai_key

# OpenAI-compatible agent tuy bien qua env
AGENT_QWEN_TYPE=openai_compatible
AGENT_QWEN_BASE_URL=http://127.0.0.1:1234/v1
AGENT_QWEN_API_KEY=local
AGENT_QWEN_MODEL=qwen2.5-vl

# LightOnOCR endpoint ngoai (goi theo local_http)
AGENT_LIGHTONOCR_TYPE=local_http
AGENT_LIGHTONOCR_BASE_URL=http://127.0.0.1:7860/ocr
AGENT_LIGHTONOCR_API_KEY=
```

Sau khi doi env, restart API + worker.

### Buoc 2: Kiem tra agent da nap

Goi:

- `GET /api/v1/agents`

Neu setup dung, danh sach se co them agent tu env nhu `qwen` va `lightonocr`.

### Buoc 3: Goi extract voi agent

Vi du goi agent da khai bao san trong env (`lightonocr`):

```json
{
  "image_base64": "<base64-image>",
  "filename": "sample.jpg",
  "agent": "lightonocr",
  "output_format": "markdown",
  "save_to_file": false,
  "options": {
    "model": null,
    "base_url": null,
    "api_key": null
  }
}
```

Vi du override runtime khong can env (local_http):

```json
{
  "image_base64": "<base64-image>",
  "filename": "sample.jpg",
  "agent": "local_http",
  "output_format": "markdown",
  "save_to_file": false,
  "options": {
    "base_url": "http://127.0.0.1:7860/ocr",
    "api_key": "optional-token",
    "model": null
  }
}
```

## Huong dan nhung API vao web/app khac

Khuyen nghi luong nhung:

1. Frontend gui `POST /api/v1/extract/json`.
2. Luu `task_id` tu response submit.
3. Poll `GET /api/v1/task-status/{task_id}` den khi `SUCCESS` hoac `FAILURE`.
4. Neu co artifact, tai file qua:
   - `GET /api/v1/task-artifact/{task_id}/json`
   - `GET /api/v1/task-artifact/{task_id}/excel`

### Mau fetch submit + poll

```js
const submitRes = await fetch("http://127.0.0.1:8000/api/v1/extract/json", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    image_base64: base64Image,
    filename: "invoice.jpg",
    agent: "lightonocr",
    output_format: "json",
    save_to_file: true,
    options: {},
  }),
});

const submitData = await submitRes.json();
const taskId = submitData.task_id;

let done = false;
while (!done) {
  const statusRes = await fetch(
    `http://127.0.0.1:8000/api/v1/task-status/${taskId}`,
  );
  const statusData = await statusRes.json();

  if (statusData.status === "SUCCESS" || statusData.status === "FAILURE") {
    done = true;
    console.log(statusData);
  } else {
    await new Promise((r) => setTimeout(r, 2000));
  }
}
```

Ghi chu production:

- Khong expose API key trong frontend public.
- Nen goi extract-pdf thong qua backend trung gian neu can bao mat key.
- Cau hinh CORS dung domain web thuc te truoc khi mo truy cap.
