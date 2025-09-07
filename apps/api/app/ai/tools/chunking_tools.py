from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
)


class TextChunkingTool:
    """Tool for chunking documents using various strategies."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the chunking tool.

        Args:
            chunk_size: Maximum size of each chunk
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Language-specific separators for better chunking
        self.language_separators = {
            "english": ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
            "spanish": ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
            "french": ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
            "german": ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
            "portuguese": ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
            "italian": ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
            "bosnian": ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
            "default": ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
        }

        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
            separators=self.language_separators["default"],
        )

    def chunk_documents(
        self, documents: List[Document], detected_language: str = None
    ) -> List[Document]:
        """
        Chunk documents using recursive character splitting with language-aware separators.

        Args:
            documents: List of documents to chunk
            detected_language: Detected language for language-specific chunking

        Returns:
            List of chunked documents with enhanced metadata

        Raises:
            ValueError: If chunking fails
        """
        try:
            print(
                f"[CHUNKING_TOOL] Starting recursive character chunking of {len(documents)} documents (language: {detected_language})"
            )

            # Create language-specific splitter if language is detected
            if detected_language and detected_language in self.language_separators:
                print(
                    f"[CHUNKING_TOOL] Using language-specific separators for {detected_language}"
                )
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    length_function=len,
                    is_separator_regex=False,
                    separators=self.language_separators[detected_language],
                )
            else:
                print(
                    f"[CHUNKING_TOOL] Using default separators for unknown language: {detected_language}"
                )
                splitter = self.recursive_splitter

            # DEBUG: Log input document details
            total_input_chars = sum(len(doc.page_content) for doc in documents)
            print(f"[CHUNKING_TOOL] Input: {total_input_chars} total characters")

            chunked_docs = splitter.split_documents(documents)

            print(
                f"[CHUNKING_TOOL] Recursive splitter produced {len(chunked_docs)} chunks"
            )

            # DEBUG: Log output details
            if chunked_docs:
                output_chars = sum(len(chunk.page_content) for chunk in chunked_docs)
                print(
                    f"[CHUNKING_TOOL] Output: {output_chars} total characters in chunks"
                )
            else:
                print(f"[CHUNKING_TOOL] Recursive splitter returned no chunks!")

            # Add chunk metadata including language information
            for i, chunk in enumerate(chunked_docs):
                chunk.metadata.update(
                    {
                        "chunk_index": i,
                        "chunk_size": len(chunk.page_content),
                        "chunking_method": "recursive_character",
                        "original_chunk_size": self.chunk_size,
                        "chunk_overlap": self.chunk_overlap,
                        "detected_language": detected_language or "unknown",
                        "language_aware_chunking": detected_language is not None,
                    }
                )

            return chunked_docs

        except Exception as e:
            print(f"[CHUNKING_TOOL] Recursive character chunking failed: {str(e)}")
            raise ValueError(
                f"Failed to chunk documents by recursive character splitting: {str(e)}"
            )

    def chunk_by_paragraphs(
        self, documents: List[Document], detected_language: str = None
    ) -> List[Document]:
        """
        Chunk documents by paragraphs with size limits.

        Args:
            documents: List of documents to chunk

        Returns:
            List of paragraph-based chunks
        """
        try:
            print(
                f"[CHUNKING_TOOL] Starting paragraph-based chunking of {len(documents)} documents (language: {detected_language})"
            )

            # Create language-specific splitter if language is detected
            if detected_language and detected_language in self.language_separators:
                print(
                    f"[CHUNKING_TOOL] Using language-specific separators for {detected_language}"
                )
                paragraph_splitter = CharacterTextSplitter(
                    separator="\n\n",
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    length_function=len,
                    separators=self.language_separators[detected_language],
                )
            else:
                print(
                    f"[CHUNKING_TOOL] Using default separators for unknown language: {detected_language}"
                )
                paragraph_splitter = CharacterTextSplitter(
                    separator="\n\n",
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                    length_function=len,
                )

            # DEBUG: Log input document details
            total_input_chars = sum(len(doc.page_content) for doc in documents)
            paragraph_count = sum(doc.page_content.count("\n\n") for doc in documents)
            print(
                f"[CHUNKING_TOOL] Input: {total_input_chars} total characters, {paragraph_count} paragraph breaks"
            )

            chunked_docs = paragraph_splitter.split_documents(documents)

            print(
                f"[CHUNKING_TOOL] Paragraph splitter produced {len(chunked_docs)} chunks"
            )

            # DEBUG: Log output details
            if chunked_docs:
                output_chars = sum(len(chunk.page_content) for chunk in chunked_docs)
                print(
                    f"[CHUNKING_TOOL] Output: {output_chars} total characters in chunks"
                )
            else:
                print(f"[CHUNKING_TOOL] Paragraph splitter returned no chunks!")

            # Add chunk metadata including language information
            for i, chunk in enumerate(chunked_docs):
                chunk.metadata.update(
                    {
                        "chunk_index": i,
                        "chunk_size": len(chunk.page_content),
                        "chunking_method": "paragraph",
                        "original_chunk_size": self.chunk_size,
                        "chunk_overlap": self.chunk_overlap,
                        "detected_language": detected_language or "unknown",
                        "language_aware_chunking": detected_language is not None,
                    }
                )

            return chunked_docs

        except Exception as e:
            print(f"[CHUNKING_TOOL] Paragraph chunking failed: {str(e)}")
            raise ValueError(f"Failed to chunk documents by paragraphs: {str(e)}")

    def adaptive_chunk(
        self,
        documents: List[Document],
        content_type: str,
        detected_language: str = None,
    ) -> List[Document]:
        """
        Apply adaptive chunking based on content type and detected language.

        Args:
            documents: List of documents to chunk
            content_type: Type of content (pdf, docx, excel, text, etc.)
            detected_language: Detected language for language-aware chunking

        Returns:
            List of adaptively chunked documents
        """
        print(
            f"[CHUNKING_TOOL] Adaptive chunking for content type: '{content_type}', language: '{detected_language}'"
        )

        # Adjust chunking strategy based on content type
        if content_type == "pdf":
            # PDFs often have better paragraph structure
            print(f"[CHUNKING_TOOL] Using paragraph chunking for PDF")
            return self.chunk_by_paragraphs(documents, detected_language)
        elif content_type == "docx":
            # DOCX files usually have good section breaks
            print(f"[CHUNKING_TOOL] Using paragraph chunking for DOCX")
            return self.chunk_by_paragraphs(documents, detected_language)
        elif content_type == "excel":
            # Excel models have structured sections (sheets, metrics, analysis)
            # Use paragraph chunking to preserve section boundaries
            print(f"[CHUNKING_TOOL] Using paragraph chunking for Excel")
            return self.chunk_by_paragraphs(documents, detected_language)
        elif content_type == "text":
            # Plain text may need more aggressive splitting
            print(f"[CHUNKING_TOOL] Using recursive character chunking for text")
            return self.chunk_documents(documents, detected_language)
        elif content_type == "csv":
            # CSV files may have structured data
            print(f"[CHUNKING_TOOL] Using paragraph chunking for CSV")
            return self.chunk_documents(documents, detected_language)
        else:
            # Default to recursive splitting
            print(
                f"[CHUNKING_TOOL] Using default recursive character chunking for unknown type"
            )
            return self.chunk_documents(documents, detected_language)
