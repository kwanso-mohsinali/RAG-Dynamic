from typing import List, Optional
from pathlib import Path
from langchain_community.document_loaders import CSVLoader
from langchain_core.documents import Document


class CSVExtractionTool:
    """Tool for extracting and processing CSV documents."""

    def extract_text(
        self,
        file_path: str,
        original_filename: Optional[str] = None,
        csv_delimiter: str = ",",
    ) -> List[Document]:
        """
        Extract data from a CSV file.

        Args:
            file_path: Path to CSV file (may be temporary)
            original_filename: Original filename from database (optional)
            csv_delimiter: Delimiter used in the CSV (default: ",")
            encoding: CSV file encoding (auto-detected if None)

        Returns:
            List of Document objects with content and metadata
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        try:
            loader = CSVLoader(
                file_path=file_path,
                csv_args={"delimiter": csv_delimiter},
            )
            documents = loader.load()
            print(
                f"[CSV_EXTRACTION] Extracted {len(documents)} documents from {file_path}"
            )

            # Use original filename if provided, otherwise use file path
            source_filename = (
                original_filename if original_filename else Path(file_path).name
            )
            print(f"[CSV_EXTRACTION] Source filename: {source_filename}")

            # Enhance metadata for each document
            for doc in documents:
                doc.metadata.update(
                    {
                        "file_type": "csv",
                        "file_path": file_path,
                        "source_file": source_filename,
                        "delimiter": csv_delimiter,
                        "extraction_method": "CSVLoader",
                    }
                )

            return documents

        except Exception as e:
            print(f"[CSV_EXTRACTION] Extraction failed: {str(e)}")
            raise ValueError(f"Failed to extract CSV from file: {str(e)}")
