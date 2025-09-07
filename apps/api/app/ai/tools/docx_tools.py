from typing import List
from pathlib import Path
from langchain_community.document_loaders.word_document import Docx2txtLoader
from langchain_core.documents import Document


class DOCXExtractionTool:
    """Tool for extracting text and metadata from DOCX documents."""

    def extract_text(
        self, file_path: str, original_filename: str = None
    ) -> List[Document]:
        """
        Extract text from DOCX file using Docx2txtLoader.

        Args:
            file_path: Path to DOCX file (may be temporary)
            original_filename: Original filename from database (optional)

        Returns:
            List of Document objects with content and metadata

        Raises:
            FileNotFoundError: If DOCX file doesn't exist
            ValueError: If DOCX cannot be processed
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"DOCX file not found: {file_path}")

        try:
            loader = Docx2txtLoader(file_path)
            documents = loader.load()
            print(
                f"[DOCX_EXTRACTION] Extracted {len(documents)} documents from {file_path}"
            )

            # Use original filename if provided, otherwise use file path
            source_filename = (
                original_filename if original_filename else Path(file_path).name
            )
            print(f"[DOCX_EXTRACTION] Source filename: {source_filename}")

            # Enhance metadata for each document
            for doc in documents:
                doc.metadata.update(
                    {
                        "file_type": "docx",
                        "file_path": file_path,
                        "source_file": source_filename,  # Use original filename
                        "extraction_method": "Docx2txtLoader",
                    }
                )

            return documents

        except Exception as e:
            raise ValueError(f"Failed to extract text from DOCX: {str(e)}")
