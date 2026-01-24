import base64
from PIL import Image
import io


class ImageProcessor:
    @staticmethod
    def encode_image_base64(image_path: str) -> str:
        """
        Encodes an image file to a base64 string.
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    @staticmethod
    def validate_image_path(image_path: str):
        # Validates if image exists (can add more checks)
        pass
