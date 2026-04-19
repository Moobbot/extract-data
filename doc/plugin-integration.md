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
    options: { model: "gemini-2.5-flash" }
  })
});

const submitResult = await response.json();
```

Sau do poll:

```js
const statusResponse = await fetch(
  `http://127.0.0.1:8000/api/v1/task-status/${submitResult.task_id}`
);
const statusData = await statusResponse.json();
```

Neu task `SUCCESS`, response `result` se co:

- `content`: noi dung ket qua
- `saved_to`: duong dan JSON neu `save_to_file=true`
- `saved_excel`: duong dan Excel neu `output_format=json` va parse duoc JSON

## Luong plugin de xai trong web

1. Upload anh hoac gui `image_base64` len API.
2. Luu `task_id` va poll trang thai.
3. Hien thi ket qua va nut tai file neu co `saved_to` hoac `saved_excel`.

## Khuyen nghi production

- Khong nen nhung `OPENAI_API_KEY` hoac `GOOGLE_API_KEY` vao frontend.
- Neu can bao mat, cho web cua ban goi qua backend trung gian.
- Neu web khac dung domain rieng, hay cau hinh `CORS_ALLOW_ORIGINS` dung chinh xac domain do.