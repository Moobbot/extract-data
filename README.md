# Extract PDF API

Service trich xuat bang du lieu/structured text tu anh, ho tro nhieu AI agent qua mot API thong nhat.

## Tong quan

- Backend: FastAPI + Celery.
- Mac dinh agent: `gemini`.
- Agent built-in trong `extract-pdf`: `gemini`, `openai`, `openai_compatible`, `local_http`.
- Ho tro agent tuy bien qua env: `AGENT_<NAME>_*`.

## Kien truc tach rieng

- `extract-pdf` la API orchestration.
- `LightOnOCR` la he thong OCR doc lap ben ngoai.
- `extract-pdf` khong co built-in `lightonocr` nua.
- Neu muon goi LightOnOCR, dung adapter generic `local_http` va tro `options.base_url` vao endpoint cua LightOnOCR.

## Luu y ve UI

- `extract-pdf` co them quick UI de team test nhanh: `http://127.0.0.1:8000/ui`.
- UI de test API la Swagger: `http://127.0.0.1:8000/docs`.
- UI cua LightOnOCR nam o project/doc vu rieng cua LightOnOCR.
- Quick UI co cac nut: submit task, download JSON, download Excel, copy content, clear.

### Cach dung Quick UI

1. Mo `http://127.0.0.1:8000/ui`.
2. Chon `agent`.
3. Chon anh upload hoac nhap `image_path` local tren may server.
4. Neu can, nhap `model`, `base_url`, `api_key` trong phan options.
5. Bam `Submit Task` va doi UI poll trang thai cho den khi `SUCCESS`.

## Chuan bi moi truong

1. Env `extract-pdf`: chay web API va worker.
2. Env `lightonocr`: chay service/UI LightOnOCR doc lap.

### Env extract-pdf

```bash
conda activate extract-pdf
pip install -r requirements.txt
```

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

## Chay he thong

### API server

```bash
conda activate extract-pdf
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Celery worker

```bash
conda activate extract-pdf
celery -A app.core.celery_app.celery_app worker --loglevel=info -P solo --concurrency=1
```

Windows note:

- Celery on Windows should run with `solo` pool.
- If logs still show `SpawnPoolWorker`, stop all old Celery processes and start worker again with the command above.

Redis note:

- `extract-pdf` needs Redis running at `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`.
- If Redis is not running, `/extract/*` will accept requests but the worker cannot consume tasks.

### Kiem tra endpoint

- Health: `http://127.0.0.1:8000/`
- Docs: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

## Tich hop voi web khac nhu plugin

Neu muon gan `extract-pdf` vao mot web/app khac nhu mot plugin, co 2 cach:

1. Goi truc tiep API tu frontend neu da cau hinh `CORS_ALLOW_ORIGINS`.
2. Goi qua backend cua web do, neu muon giu API key va endpoint o server-side.

### 1. Cau hinh backend `extract-pdf`

Them domain cua web can tich hop vao `.env`:

```env
CORS_ALLOW_ORIGINS=http://localhost:3000,https://your-web-app.com
```

Restart API server sau khi doi env.

### 2. Cach goi API tu web khac

Frontend web ngoai co the goi truc tiep `POST /api/v1/extract/json` va `GET /api/v1/task-status/{task_id}`.

Vi du request:

```js
const response = await fetch("http://127.0.0.1:8000/api/v1/extract/json", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    image_base64: base64Image,
    filename: "invoice.jpg",
    agent: "gemini",
    output_format: "json",
    save_to_file: true,
    options: {
      model: "gemini-2.5-flash",
    },
  }),
});

const submitResult = await response.json();
```

Sau do poll:

```js
const statusResponse = await fetch(
  `http://127.0.0.1:8000/api/v1/task-status/${submitResult.task_id}`,
);
const statusData = await statusResponse.json();
```

Neu task `SUCCESS`, response `result` se co:

- `content`: noi dung ket qua
- `saved_to`: duong dan JSON neu `save_to_file=true`
- `saved_excel`: duong dan Excel neu `output_format=json` va parse duoc JSON

### 3. Cach dung nhu plugin trong web cua ban

`extract-pdf` co the duoc nhin nhu mot service plugin khi web cua ban lam 3 viec:

1. Upload anh hoac gui `image_base64` len API.
2. Luu `task_id` va poll trang thai.
3. Hien thi ket qua va nut tai file neu co `saved_to` hoac `saved_excel`.

### 4. Khuyen nghi khi tich hop production

- Khong nen nhung `OPENAI_API_KEY` hoac `GOOGLE_API_KEY` vao frontend.
- Neu can bao mat, cho web cua ban goi qua backend trung gian.
- Neu web khac dung domain rieng, hay cau hinh `CORS_ALLOW_ORIGINS` dung chinh xac domain do.

## Mau tich hop React/Next.js

Duoi day la mau co ban cho Next.js App Router. Cach nay phu hop khi ban muon dung `extract-pdf` nhu mot plugin frontend: upload anh, gui task, roi poll ket qua.

### 1. Bien moi truong

```env
NEXT_PUBLIC_EXTRACT_PDF_API=http://127.0.0.1:8000
```

Neu ban khong muon goi truc tiep tu browser, co the bo bien nay va tao API route trung gian trong Next.js.

### 2. Client component

```tsx
"use client";

import { useState } from "react";

type TaskResult = {
  task_id?: string;
  status?: string;
  result?: {
    content?: string;
    saved_to?: string;
    saved_excel?: string;
  };
  error?: string;
};

const API_BASE =
  process.env.NEXT_PUBLIC_EXTRACT_PDF_API ?? "http://127.0.0.1:8000";

export default function ExtractPdfWidget() {
  const [file, setFile] = useState<File | null>(null);
  const [taskId, setTaskId] = useState("");
  const [status, setStatus] = useState("idle");
  const [content, setContent] = useState("");
  const [jsonArtifactUrl, setJsonArtifactUrl] = useState("");
  const [excelArtifactUrl, setExcelArtifactUrl] = useState("");

  const submit = async () => {
    if (!file) return;

    setStatus("encoding");
    const base64 = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = String(reader.result || "");
        resolve(result.split(",")[1] ?? result);
      };
      reader.onerror = () => reject(new Error("Cannot read file"));
      reader.readAsDataURL(file);
    });

    setStatus("submitting");
    const response = await fetch(`${API_BASE}/api/v1/extract/json`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_base64: base64,
        filename: file.name,
        agent: "gemini",
        output_format: "json",
        save_to_file: true,
        options: { model: "gemini-2.5-flash" },
      }),
    });

    const submitted: TaskResult = await response.json();
    if (!response.ok) {
      throw new Error(submitted.error || "Submit failed");
    }

    setTaskId(submitted.task_id ?? "");
    setStatus("polling");

    const poll = async () => {
      const statusResponse = await fetch(
        `${API_BASE}/api/v1/task-status/${submitted.task_id}`,
      );
      const current: TaskResult = await statusResponse.json();

      if (current.status === "SUCCESS" && current.result) {
        setStatus("done");
        setContent(current.result.content ?? "");
        setJsonArtifactUrl(current.result.saved_to ?? "");
        setExcelArtifactUrl(current.result.saved_excel ?? "");
        return;
      }

      if (current.status === "FAILURE") {
        setStatus("failed");
        return;
      }

      setTimeout(poll, 2000);
    };

    poll();
  };

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <input
        type="file"
        accept="image/*"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <button onClick={submit}>Run extraction</button>
      <div>Status: {status}</div>
      {taskId ? <div>Task ID: {taskId}</div> : null}
      {content ? <pre>{content}</pre> : null}
      {jsonArtifactUrl ? (
        <a href={`${API_BASE}/api/v1/task-artifact/${taskId}/json`}>
          Download JSON
        </a>
      ) : null}
      {excelArtifactUrl ? (
        <a href={`${API_BASE}/api/v1/task-artifact/${taskId}/excel`}>
          Download Excel
        </a>
      ) : null}
    </div>
  );
}
```

### 3. Neu muon giu API key o server

Ban co the tao API route Next.js de proxy request sang `extract-pdf`, roi frontend chi goi route cua Next.js.

```ts
// app/api/extract/route.ts
import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.EXTRACT_PDF_API ?? "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const response = await fetch(`${API_BASE}/api/v1/extract/json`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
```

### 4. Ghi chu thuc te

- Neu goi truc tiep tu browser, hay bat `CORS_ALLOW_ORIGINS`.
- Neu dung proxy route Next.js, ban co the giu `extract-pdf` o private network va khong lo CORS.
- Duong dan tai file da co san qua `/api/v1/task-artifact/{task_id}/json` va `/api/v1/task-artifact/{task_id}/excel`.

## API chinh

- `GET /api/v1/agents`
- `POST /api/v1/extract`
- `POST /api/v1/extract/batch`
- `POST /api/v1/extract/folder`
- `POST /api/v1/extract/json`
- `GET /api/v1/task-status/{task_id}`

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

## Agent tuy bien bang env

```env
AGENT_QWEN_TYPE=openai_compatible
AGENT_QWEN_BASE_URL=http://127.0.0.1:1234/v1
AGENT_QWEN_API_KEY=local
AGENT_QWEN_MODEL=qwen2.5-vl
```

Khi goi API, dung `agent = qwen`.

## CLI local script

```bash
python simple_extractor.py path/to/image.png --agent gemini
python simple_extractor.py path/to/image.png --agent openai --model gpt-4o
python simple_extractor.py path/to/image.png --agent openai_compatible --base-url http://127.0.0.1:1234/v1 --api-key local --model qwen2.5-vl
python simple_extractor.py path/to/image.png --agent local_http --base-url http://127.0.0.1:8080/ocr
```

Khi chay CLI voi `--format json`, script se luu JSON va xuat them Excel `.xlsx` neu du lieu parse duoc.

## Ghi chu van hanh

- Docs cua `extract-pdf` nam tren port API (hien tai la 8000).
- `http://127.0.0.1:8080/docs` co the 404 neu do la OCR service khong expose docs.
