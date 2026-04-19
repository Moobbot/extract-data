# Mau React/Next.js

Duoi day la mau co ban cho Next.js App Router de dung `extract-pdf` nhu plugin frontend.

## Bien moi truong

```env
NEXT_PUBLIC_EXTRACT_PDF_API=http://127.0.0.1:8000
```

## Client component (submit + poll + download)

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

const API_BASE = process.env.NEXT_PUBLIC_EXTRACT_PDF_API ?? "http://127.0.0.1:8000";

export default function ExtractPdfWidget() {
  const [file, setFile] = useState<File | null>(null);
  const [taskId, setTaskId] = useState("");
  const [status, setStatus] = useState("idle");
  const [content, setContent] = useState("");

  const submit = async () => {
    if (!file) return;

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
        options: { model: "gemini-2.5-flash" }
      })
    });

    const submitted: TaskResult = await response.json();
    if (!response.ok) throw new Error(submitted.error || "Submit failed");

    setTaskId(submitted.task_id ?? "");
    setStatus("polling");

    const poll = async () => {
      const res = await fetch(`${API_BASE}/api/v1/task-status/${submitted.task_id}`);
      const current: TaskResult = await res.json();

      if (current.status === "SUCCESS" && current.result) {
        setStatus("done");
        setContent(current.result.content ?? "");
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
    <div>
      <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      <button onClick={submit}>Run extraction</button>
      <div>Status: {status}</div>
      {taskId ? <div>Task ID: {taskId}</div> : null}
      {content ? <pre>{content}</pre> : null}
      {taskId ? <a href={`${API_BASE}/api/v1/task-artifact/${taskId}/json`}>Download JSON</a> : null}
      {taskId ? <a href={`${API_BASE}/api/v1/task-artifact/${taskId}/excel`}>Download Excel</a> : null}
    </div>
  );
}
```

## Proxy qua Next.js route (server-side)

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

## Luu y

- Goi truc tiep tu browser can cau hinh `CORS_ALLOW_ORIGINS`.
- Goi qua proxy route Next.js se de bao mat hon cho production.
