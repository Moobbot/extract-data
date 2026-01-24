from abc import ABC, abstractmethod


class AIProvider(ABC):
    @abstractmethod
    def generate_content(self, image_path: str, prompt: str) -> str:
        """
        Generates content from an image based on the prompt.
        """
        pass
