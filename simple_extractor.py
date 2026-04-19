import os
import json
import argparse
from dotenv import load_dotenv
import pandas as pd
from app.services.ai_providers import AIProviderFactory

load_dotenv()

# --- Configuration ---
# Example: HARDCODED_IMAGE_PATH = "datasets/Hinh04.jpg"
HARDCODED_IMAGE_PATH = "datasets/Hinh09.jpg"
# Example: HARDCODED_OUTPUT_PATH = "outputs"
HARDCODED_OUTPUT_PATH = "outputs"
# Output format: 'markdown' or 'json'
HARDCODED_OUTPUT_FORMAT = "markdown"


# --- Prompts ---
def get_prompt(output_format):
    """
    Returns the appropriate prompt based on the desired output format.
    """
    if output_format == "json":
        return """
        Analyze this image. Identify any tables or structured data.
        Extract the data and return it ONLY as a valid JSON object.
        Do not include markdown formatting (like ```json).
        The JSON should be a list of objects or a structured dictionary suitable for the data.
        """
    else:
        return """
        Analyze this image. Identify any tables or structured data.
        Extract the data and return it as a Markdown table.
        Return ONLY the markdown content.
        Do not wrap it in ```markdown code blocks.
        """


# --- Helper Functions ---
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


def save_to_excel(data, output_filename):
    """
    Saves JSON data to an Excel file.
    Handles both list of dicts (single sheet) and dict of lists (multiple sheets).
    """
    try:
        excel_filename = os.path.splitext(output_filename)[0] + ".xlsx"
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

        if sheets:
            with pd.ExcelWriter(excel_filename, engine="openpyxl") as writer:
                for sheet_name, df in sheets.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"Saved Excel result to {excel_filename}")
        else:
            print("No structured data found to save to Excel.")

    except Exception as e:
        print(f"Error saving to Excel: {e}")


def save_results(raw_result, output_base, output_format):
    """
    Saves the extracted results to files based on the format.
    """
    # Always clean output first
    cleaned_result = clean_json_string(raw_result)

    if output_format == "markdown":
        md_filename = output_base + ".md"
        with open(md_filename, "w", encoding="utf-8") as f:
            f.write(cleaned_result)
        print(f"\nSaved Markdown result to {md_filename}")
        print("\n--- Output Preview ---\n")
        print(
            cleaned_result[:500] + "..."
            if len(cleaned_result) > 500
            else cleaned_result
        )

    else:  # JSON format
        try:
            data = json.loads(cleaned_result)
            print(json.dumps(data, indent=2, ensure_ascii=False))

            # Save JSON
            json_filename = output_base + ".json"
            with open(json_filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"\nSaved JSON result to {json_filename}")

            # Save Excel
            save_to_excel(data, json_filename)

        except json.JSONDecodeError:
            print("Warning: Could not parse JSON. Raw output:")
            print(raw_result)


def call_ai_service(agent, image_path, prompt, model=None, base_url=None, api_key=None):
    """
    Dispatches the call to the appropriate AI provider.
    """
    agent_config = {
        "model": model,
        "base_url": base_url,
        "api_key": api_key,
    }
    agent_config = {k: v for k, v in agent_config.items() if v}

    provider = AIProviderFactory.get_provider(agent, agent_config)
    return provider.generate_content(image_path, prompt)


# --- Pipeline ---
def run_extraction_pipeline(
    image_path,
    output_path,
    agent,
    output_format,
    model=None,
    base_url=None,
    api_key=None,
):
    """
    Orchestrates the entire extraction process.
    """
    # 1. Validation
    if not image_path:
        print("Error: No image path provided.")
        return
    if not os.path.exists(image_path):
        print(f"Error: File not found at {image_path}")
        return

    print(f"Processing {image_path} using {agent} (format: {output_format})...")

    # 2. Get Prompt
    prompt = get_prompt(output_format)

    # 3. Call AI Service
    try:
        raw_result = call_ai_service(
            agent=agent,
            image_path=image_path,
            prompt=prompt,
            model=model,
            base_url=base_url,
            api_key=api_key,
        )
    except Exception as e:
        print(f"An error occurred during AI processing: {e}")
        return

    # 4. Prepare Output Path
    image_basename = os.path.basename(image_path)
    base_filename = os.path.splitext(image_basename)[0]

    if output_path:
        os.makedirs(output_path, exist_ok=True)
        output_base = os.path.join(output_path, base_filename)
    else:
        output_base = os.path.splitext(image_path)[0]

    # 5. Save Results
    save_results(raw_result, output_base, output_format)


# --- Main ---
def main():
    parser = argparse.ArgumentParser(
        description="Extract tables from image to JSON/Excel or Markdown using AI."
    )
    parser.add_argument("image_path", nargs="?", help="Path to the image file.")
    parser.add_argument("output_path", nargs="?", help="Path to save the output.")
    parser.add_argument(
        "--agent",
        default=os.getenv("AI_PROVIDER", "gemini"),
        help="Agent/provider name (gemini, openai, openai_compatible, local_http, or AGENT_<NAME> env config).",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Backward-compatible alias of --agent.",
    )
    parser.add_argument(
        "--model", default=None, help="Model override for the selected agent."
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Base URL for OpenAI-compatible endpoints.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key override for the selected agent.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default=HARDCODED_OUTPUT_FORMAT,
        help="Output format (json or markdown).",
    )
    args = parser.parse_args()

    # Apply hardcoded defaults if arguments are missing
    target_path = args.image_path or HARDCODED_IMAGE_PATH
    output_path = args.output_path or HARDCODED_OUTPUT_PATH

    selected_agent = args.provider or args.agent
    run_extraction_pipeline(
        target_path,
        output_path,
        selected_agent,
        args.format,
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
    )


if __name__ == "__main__":
    main()
