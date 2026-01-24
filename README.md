# Simplified Table Extractor

A lightweight tool to extract table data from images using Google Gemini or OpenAI GPT models.

## Features

- **AI-Powered**: Uses Gemini 1.5 Flash or GPT-4o for accurate extraction.
- **Simple**: Single script, minimal dependencies.
- **Flexible**: Choose your preferred AI provider.

## Setup

1.  **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure API Keys**:
    - Rename `.env.example` to `.env`.
    - Add your **Google API Key** or **OpenAI API Key**.

    ```env
    GOOGLE_API_KEY=your_key_here
    # or
    OPENAI_API_KEY=your_key_here
    ```

## Usage

```bash
# Default (Gemini)
python simple_extractor.py path/to/image.png

# Use OpenAI
python simple_extractor.py path/to/image.png --provider openai
```

The script will:

1.  Read the image.
2.  Send it to the AI.
3.  Print the JSON result to console.
4.  Save the JSON to `path/to/image.json`.
