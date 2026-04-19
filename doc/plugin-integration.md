# Tich hop plugin web khac

Neu muon gan `extract-pdf` vao mot web/app khac nhu mot plugin, co 2 cach:

1. Goi truc tiep API tu frontend neu da cau hinh `CORS_ALLOW_ORIGINS`.
2. Goi qua backend cua web do, neu muon giu API key va endpoint o server-side.

## Cach goi API tu web khac

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
    options: { model: "gemini-2.5-flash" },
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

## Setup API Agent cho plugin truoc khi nhung

Ban co 2 cach cau hinh agent:

1. Khai bao co dinh qua env tren server extract-pdf.
2. Truyen runtime qua `options` trong moi request.

### Mau env cho agent co dinh

```env
AGENT_LIGHTONOCR_TYPE=local_http
AGENT_LIGHTONOCR_BASE_URL=http://127.0.0.1:9000/ocr
AGENT_LIGHTONOCR_API_KEY=
```

Khi do frontend chi can gui `agent: "lightonocr"`.

### Mau runtime khong can env

```json
{
  "agent": "local_http",
  "options": {
    "base_url": "http://127.0.0.1:9000/ocr",
    "api_key": "optional-token"
  }
}
```

## Huong dan nhung LightOnOCR vao web/app

Muc tieu: dung extract-pdf nhu gateway, LightOnOCR la he OCR ben ngoai.

1. Chay LightOnOCR service rieng va dam bao endpoint nhan `image_base64`, `prompt`.
2. Tu web/app, goi `POST /api/v1/extract/json` cua extract-pdf voi `agent = lightonocr` (hoac `local_http`).
3. Poll `GET /api/v1/task-status/{task_id}`.
4. Hien thi `result.content` hoac hien nut tai artifact neu co.

Vi du payload khi nhung LightOnOCR:

```json
{
  "image_base64": "<base64-image>",
  "filename": "soa_page_1.jpg",
  "agent": "lightonocr",
  "output_format": "markdown",
  "save_to_file": false,
  "options": {}
}
```

## Luong plugin de xai trong web

1. Upload anh hoac gui `image_base64` len API.
2. Luu `task_id` va poll trang thai.
3. Hien thi ket qua va nut tai file neu co `saved_to` hoac `saved_excel`.

## Khuyen nghi production

- Khong nen nhung `OPENAI_API_KEY` hoac `GOOGLE_API_KEY` vao frontend.
- Neu can bao mat, cho web cua ban goi qua backend trung gian.
- Neu web khac dung domain rieng, hay cau hinh `CORS_ALLOW_ORIGINS` dung chinh xac domain do.
