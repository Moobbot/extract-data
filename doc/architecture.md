# Kiến trúc Provider

## Tổng quan

```
app/services/
├── ai_providers.py          ← shim backward-compat (re-export từ providers/)
├── providers/
│   ├── __init__.py          ← public exports
│   ├── base.py              ← AIProvider ABC
│   ├── gemini.py            ← GeminiProvider
│   ├── openai_provider.py   ← OpenAIProvider
│   ├── local_http.py        ← LocalHTTPProvider
│   ├── lightonocr.py        ← LightOnOCRProvider
│   └── factory.py           ← AIProviderFactory
└── image_processor.py
```

## Base class — `providers/base.py`

```python
class AIProvider(ABC):
    @abstractmethod
    def generate_content(self, image_path: str, prompt: str) -> Union[str, dict]:
        ...
```

`generate_content()` có thể trả về:

- **`str`** — text thuần (Gemini, OpenAI, LocalHTTP)
- **`dict`** — kết quả có cấu trúc + metadata (LightOnOCR):
  ```json
  {
    "text": "...",
    "api_json_path": "/tmp/.../file.json",
    "api_excel_path": "/tmp/.../file.xlsx",
    "base_url": "http://lightonocr:7861"
  }
  ```

## Providers

| Class                | File                 | Protocol                 | Input      | Output |
| -------------------- | -------------------- | ------------------------ | ---------- | ------ |
| `GeminiProvider`     | `gemini.py`          | Google AI API            | PIL Image  | `str`  |
| `OpenAIProvider`     | `openai_provider.py` | OpenAI Chat API          | base64     | `str`  |
| `LocalHTTPProvider`  | `local_http.py`      | HTTP JSON POST           | base64     | `str`  |
| `LightOnOCRProvider` | `lightonocr.py`      | HTTP multipart/form-data | file bytes | `dict` |

## Factory — `providers/factory.py`

```python
# Lấy provider theo tên
provider = AIProviderFactory.get_provider("lightonocr", config)
result = provider.generate_content(image_path, prompt)

# Liệt kê tất cả agent
agents = AIProviderFactory.list_available_agents()
```

**Registry nội bộ:**

```python
_BUILDERS = {
    "gemini":            _build_gemini,
    "openai":            _build_openai,
    "openai_compatible": _build_openai_compatible,
    "local_http":        _build_local_http,
    "lightonocr":        _build_lightonocr,
}
```

**Độ ưu tiên khi resolve:**

1. Builtin (`_BUILDERS`)
2. Env-configured (`AGENT_<NAME>_TYPE`)
3. Fallback OpenAI-compatible nếu có đủ `api_key + base_url + model`

## Thêm provider mới

1. Tạo file `app/services/providers/my_provider.py` kế thừa `AIProvider`
2. Implement `generate_content()`
3. Đăng ký trong `factory.py`:
   ```python
   _BUILDERS = {
       ...
       "my_provider": _build_my_provider,
   }
   ```
4. Thêm static method `_build_my_provider(config)` vào `AIProviderFactory`
5. Export trong `providers/__init__.py`

## Backward compatibility

`app/services/ai_providers.py` và `app/core/interfaces.py` là các shim:

```python
# Cả hai đều hoạt động bình thường
from app.services.ai_providers import AIProviderFactory
from app.core.interfaces import AIProvider
```

Không cần sửa code cũ đang dùng hai import path này.
