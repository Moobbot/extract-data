import os
import json
import argparse
from dotenv import load_dotenv
from PIL import Image
from google import genai
import pandas as pd

# Optional: Import OpenAI if you want to use GPT
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

load_dotenv()


def extract_with_gemini(image_path, api_key):
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")

    client = genai.Client(api_key=api_key)

    prompt = """
    Analyze this image. Identify any tables or structured data.
    Extract the data and return it ONLY as a valid JSON object.
    Do not include markdown formatting (like ```json).
    The JSON should be a list of objects or a structured dictionary suitable for the data.
    """

    img = Image.open(image_path)

    # Try best-first order
    candidate_models = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-flash-latest",
        "gemini-2.5-pro",
        "gemini-pro-latest",
    ]

    last_err = None
    for m in candidate_models:
        try:
            resp = client.models.generate_content(
                model=m,
                contents=[prompt, img],
            )
            return resp.text
        except Exception as e:
            last_err = e

    raise RuntimeError(f"All Gemini model attempts failed. Last error: {last_err}")


def extract_with_gpt(image_path, api_key):
    """
    Extracts table data from an image using OpenAI GPT-4o.
    """
    if not OpenAI:
        raise ImportError("openai module not installed.")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")

    client = OpenAI(api_key=api_key)

    # We need to encode image to base64 for OpenAI (or pass URL, but local file usually requires base64)
    import base64

    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    base64_image = encode_image(image_path)

    prompt = """
    Analyze this image. Identify any tables or structured data.
    Extract the data and return it ONLY as a valid JSON object.
    Do not include markdown formatting (like ```json).
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=4096,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error calling OpenAI: {str(e)}"


def save_to_excel(data, output_filename):
    """
    Saves JSON data to an Excel file.
    Handles both list of dicts (single sheet) and dict of lists (multiple sheets).
    """
    try:
        excel_filename = os.path.splitext(output_filename)[0] + ".xlsx"

        # Determine data structure for Pandas
        sheets = {}  # {sheet_name: dataframe}

        if isinstance(data, list):
            # Simple list of dicts -> Single sheet
            sheets["Sheet1"] = pd.DataFrame(data)

        elif isinstance(data, dict):
            # Dict root -> Check for lists inside
            found_list = False
            for key, value in data.items():
                if (
                    isinstance(value, list)
                    and len(value) > 0
                    and isinstance(value[0], dict)
                ):
                    # Valid list of dicts found -> New sheet
                    sheet_name = str(key)[:30]  # Excel limit is 31 chars
                    sheets[sheet_name] = pd.DataFrame(value)
                    found_list = True

            # If no lists found, or just flat dict, try to wrap the whole dict
            if not found_list:
                sheets["Sheet1"] = pd.DataFrame([data])

        else:
            sheets["Sheet1"] = pd.DataFrame([{"result": "Data is not a list or dict"}])

        # Write to Excel with multiple sheets
        if sheets:
            with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
                for sheet_name, df in sheets.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"Saved Excel result to {excel_filename}")
        else:
            print("No structured data found to save to Excel.")

    except Exception as e:
        print(f"Error saving to Excel: {e}")


def clean_json_string(s):
    """
    Clean up markdown code blocks if the LLM includes them despite instructions.
    """
    s = s.strip()
    if s.startswith("```json"):
        s = s[7:]
    if s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


# Image Configuration
# Set this to a file path to run without command line arguments
# Example: HARDCODED_IMAGE_PATH = "C:/Users/User/Downloads/table.png"
HARDCODED_IMAGE_PATH = "datasets/Hinh04.jpg"
# Example: HARDCODED_OUTPUT_PATH = "datasets/output.json"
HARDCODED_OUTPUT_PATH = "outputs"


def main():
    parser = argparse.ArgumentParser(
        description="Extract tables from image to JSON using AI."
    )
    # Make image_path optional (nargs='?')
    parser.add_argument("image_path", nargs="?", help="Path to the image file.")
    parser.add_argument("output_path", nargs="?", help="Path to save the JSON output.")
    parser.add_argument(
        "--provider",
        choices=["gemini", "openai"],
        default=os.getenv("AI_PROVIDER", "gemini"),
        help="AI Provider to use.",
    )
    args = parser.parse_args()

    # logic to choose path
    target_path = args.image_path or HARDCODED_IMAGE_PATH
    output_path = args.output_path or HARDCODED_OUTPUT_PATH

    if not target_path:
        print("Error: No image path provided.")
        print("Usage: python simple_extractor.py <image_path>")
        print("OR set HARDCODED_IMAGE_PATH in the script.")
        return

    if not os.path.exists(target_path):
        print(f"Error: File not found at {target_path}")
        return

    print(f"Processing {target_path} using {args.provider}...")

    try:
        raw_result = ""
        if args.provider == "gemini":
            api_key = os.getenv("GOOGLE_API_KEY")
            raw_result = extract_with_gemini(target_path, api_key)
        elif args.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            raw_result = extract_with_gpt(target_path, api_key)

        # Parse and pretty print
        cleaned_result = clean_json_string(raw_result)
        try:
            data = json.loads(cleaned_result)
            print(json.dumps(data, indent=2, ensure_ascii=False))

            # Save to file
            # Determine output directory and filename
            image_basename = os.path.basename(target_path)
            json_filename = os.path.splitext(image_basename)[0] + ".json"

            if output_path:
                # If output_path is set, treat it as a folder
                os.makedirs(output_path, exist_ok=True)
                output_filename = os.path.join(output_path, json_filename)
            else:
                # Default to same directory as input image
                output_filename = os.path.splitext(target_path)[0] + ".json"

            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\nSaved JSON result to {output_filename}")

            # Save to Excel
            save_to_excel(data, output_filename)

        except json.JSONDecodeError:
            print("Warning: Could not parse JSON. Raw output:")
            print(raw_result)

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
