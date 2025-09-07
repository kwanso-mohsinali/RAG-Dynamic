from typing import List, Optional
from pathlib import Path
from langchain_community.document_loaders import TextLoader, UnstructuredMarkdownLoader
from langchain_core.documents import Document


class TextExtractionTool:
    """Tool for extracting and processing plain text documents."""

    def extract_text(
        self,
        file_path: str,
        original_filename: str = None,
        encoding: Optional[str] = None,
    ) -> List[Document]:
        """
        Extract text from plain text file.

        Args:
            file_path: Path to text file (may be temporary)
            original_filename: Original filename from database (optional)
            encoding: Text encoding (auto-detected if None)

        Returns:
            List of Document objects with content and metadata

        Raises:
            FileNotFoundError: If text file doesn't exist
            ValueError: If text cannot be processed
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Text file not found: {file_path}")

        # Detect encoding if not provided
        if encoding is None:
            encoding = self.detect_encoding(file_path)

        try:
            loader = TextLoader(file_path, encoding=encoding)
            documents = loader.load()

            print(
                f"[TEXT_EXTRACTION] Extracted {len(documents)} documents from {file_path}"
            )

            # Use original filename if provided, otherwise use file path
            source_filename = (
                original_filename if original_filename else Path(file_path).name
            )
            print(f"[TEXT_EXTRACTION] Source filename: {source_filename}")

            # Enhance metadata for each document
            for doc in documents:
                doc.metadata.update(
                    {
                        "file_type": "text",
                        "file_path": file_path,
                        "source_file": source_filename,  # Use original filename
                        "encoding": encoding,
                        "extraction_method": "TextLoader",
                    }
                )

            return documents

        except Exception as e:
            print(f"[TEXT_EXTRACTION] Extraction failed: {str(e)}")
            raise ValueError(f"Failed to extract text from file: {str(e)}")

    def extract_markdown(
        self, file_path: str, original_filename: str = None
    ) -> List[Document]:
        """
        Extract text from markdown file.
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Markdown file not found: {file_path}")

        try:
            loader = UnstructuredMarkdownLoader(file_path)
            documents = loader.load()

            print(
                f"[MARKDOWN_EXTRACTION] Extracted {len(documents)} documents from {file_path}"
            )

            # Use original filename if provided, otherwise use file path
            source_filename = (
                original_filename if original_filename else Path(file_path).name
            )
            print(f"[MARKDOWN_EXTRACTION] Source filename: {source_filename}")

            # Enhance metadata for each document
            for doc in documents:
                doc.metadata.update(
                    {
                        "file_type": "markdown",
                        "file_path": file_path,
                        "source_file": source_filename,  # Use original filename
                        "extraction_method": "UnstructuredMarkdownLoader",
                    }
                )

            return documents

        except Exception as e:
            print(f"[MARKDOWN_EXTRACTION] Extraction failed: {str(e)}")
            raise ValueError(f"Failed to extract text from file: {str(e)}")

    def detect_encoding(self, file_path: str) -> str:
        """
        Detect text file encoding.

        Args:
            file_path: Path to text file

        Returns:
            Detected encoding string
        """
        try:
            # Try to import chardet for encoding detection
            import chardet

            with open(file_path, "rb") as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                return result["encoding"] or "utf-8"

        except ImportError:
            # Fallback: try common encodings
            encodings = ["utf-8", "ascii", "latin-1", "cp1252"]

            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        f.read()
                    return encoding
                except UnicodeDecodeError:
                    continue

            # Default fallback
            return "utf-8"
        except Exception:
            return "utf-8"
