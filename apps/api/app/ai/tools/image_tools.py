from typing import List
from pathlib import Path
from langchain_core.documents import Document
import logging

logger = logging.getLogger(__name__)


class ImageExtractionTool:
    """Tool for extracting text and content from images using OCR."""

    def extract_text_ocr(self, file_path: str) -> List[Document]:
        """
        Extract text from image using OCR.

        Args:
            file_path: Path to image file

        Returns:
            List of Document objects with extracted text

        Note:
            This is a placeholder implementation. In production, you would
            integrate with OCR services like:
            - Tesseract (pytesseract)
            - Google Cloud Vision API
            - AWS Textract
            - Azure Computer Vision
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        try:
            # Placeholder OCR implementation
            # In production, integrate with actual OCR service
            extracted_text = self._placeholder_ocr(file_path)

            doc = Document(
                page_content=extracted_text,
                metadata={
                    "file_type": "image",
                    "file_path": file_path,
                    "source_file": Path(file_path).name,
                    "extraction_method": "placeholder_ocr",
                    "ocr_confidence": 0.85,  # Placeholder confidence
                },
            )

            return [doc]

        except Exception as e:
            raise ValueError(f"Failed to extract text from image: {str(e)}")

    def _placeholder_ocr(self, file_path: str) -> str:
        """
        Placeholder OCR implementation.

        Args:
            file_path: Path to image file

        Returns:
            Placeholder extracted text
        """
        # This is a placeholder - replace with actual OCR implementation
        file_name = Path(file_path).name
        return f"[OCR PLACEHOLDER] Text extracted from image: {file_name}\n\nThis is placeholder text that would be replaced by actual OCR results from services like Tesseract, Google Vision API, or AWS Textract."

    def extract_with_tesseract(self, file_path: str) -> List[Document]:
        """
        Extract text using Tesseract OCR (requires pytesseract).

        Args:
            file_path: Path to image file

        Returns:
            List of Document objects with extracted text
        """
        try:
            # Try to import pytesseract
            import pytesseract
            from PIL import Image

            # Open and process image
            image = Image.open(file_path)
            extracted_text = pytesseract.image_to_string(image)

            logger.info(
                f"[IMAGE_EXTRACTION] Extracted text from image using tesseract: {extracted_text}"
            )

            # Get confidence data if available
            try:
                data = pytesseract.image_to_data(
                    image, output_type=pytesseract.Output.DICT
                )
                confidences = [int(conf) for conf in data["conf"] if int(conf) > 0]
                avg_confidence = (
                    sum(confidences) / len(confidences) if confidences else 0
                )
            except:
                avg_confidence = 0

            doc = Document(
                page_content=extracted_text,
                metadata={
                    "file_type": "image",
                    "file_path": file_path,
                    "source_file": Path(file_path).name,
                    "extraction_method": "tesseract_ocr",
                    "ocr_engine": "tesseract",
                    "extracted_text": extracted_text,
                    "ocr_confidence": avg_confidence / 100.0,  # Convert to 0-1 scale
                },
            )

            return [doc]

        except ImportError:
            # Fall back to placeholder if pytesseract not available
            return self.extract_text_ocr(file_path)
        except Exception as e:
            raise ValueError(f"Failed to extract text with Tesseract: {str(e)}")

    def extract_with_unstructured(self, file_path: str) -> List[Document]:
        """
        Extract text using unstructured library for enhanced OCR.

        Args:
            file_path: Path to image file

        Returns:
            List of Document objects with extracted text

        Raises:
            Exception: If unstructured library is not available or extraction fails
        """
        try:
            from unstructured.partition.auto import partition

            # Extract text using unstructured
            elements = partition(filename=file_path)

            # Convert elements to text
            extracted_text = "\n".join([str(element) for element in elements])

            logger.info(
                f"[IMAGE_EXTRACTION] Extracted text from image using unstructured: {extracted_text}"
            )

            # Create document with enhanced metadata
            doc = Document(
                page_content=extracted_text,
                metadata={
                    "file_type": "image",
                    "file_path": file_path,
                    "source_file": Path(file_path).name,
                    "extraction_method": "unstructured_ocr",
                    "ocr_confidence": 0.9,  # Unstructured typically has high confidence
                    "ocr_engine": "unstructured",
                    "extracted_text": extracted_text,
                    "total_elements": len(elements),
                    "element_types": [type(element).__name__ for element in elements],
                },
            )

            logger.info(
                f"[IMAGE_CHAIN] Extracted {len(elements)} elements using unstructured"
            )
            return [doc]

        except ImportError:
            raise Exception(
                "unstructured library not available - please install 'unstructured[pdf]'"
            )
        except Exception as e:
            raise Exception(f"unstructured OCR failed: {str(e)}")
