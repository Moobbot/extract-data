class PromptManager:
    @staticmethod
    def get_prompt(output_format: str) -> str:
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
        elif output_format == "markdown":
            return """
            Analyze this image. Identify any tables or structured data.
            Extract the data and return it as a Markdown table.
            Return ONLY the markdown content.
            Do not wrap it in ```markdown code blocks.
            """
        else:
            # Default fallback
            return """
            Analyze this image. Identify any tables or structured data.
            Extract the data and return it as a Markdown table.
            """
