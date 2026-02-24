#!/usr/bin/env python3
"""
PDF Text Extraction Utility

Extracts text from PDF documents for FCC filings and other regulatory documents.
Supports multiple extraction methods with fallbacks.

Dependencies:
    pip install pdfplumber PyPDF2

Usage:
    from pdf_extractor import extract_pdf_text

    # From file
    text = extract_pdf_text_from_file("/path/to/filing.pdf")

    # From bytes
    text = extract_pdf_text(pdf_bytes)

    # From URL
    text = extract_pdf_text_from_url("https://example.com/filing.pdf")
"""

from __future__ import annotations
import io
import os
import sys
import urllib.request
from datetime import datetime
from typing import Optional, Dict, List, Tuple


def log(msg: str):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ============================================================================
# PDF Extraction Methods
# ============================================================================

def extract_with_pdfplumber(pdf_bytes: bytes) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract text using pdfplumber (best for scanned/image PDFs).
    Returns (text, error).
    """
    try:
        import pdfplumber
    except ImportError:
        return None, "pdfplumber not installed"

    try:
        text_parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {i+1} ---\n{page_text}")

        if text_parts:
            return "\n\n".join(text_parts), None
        return None, "No text extracted"

    except Exception as e:
        return None, str(e)


def extract_with_pypdf2(pdf_bytes: bytes) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract text using PyPDF2 (good for text-based PDFs).
    Returns (text, error).
    """
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return None, "PyPDF2 not installed"

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text_parts = []

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- Page {i+1} ---\n{page_text}")

        if text_parts:
            return "\n\n".join(text_parts), None
        return None, "No text extracted"

    except Exception as e:
        return None, str(e)


def extract_with_pdfminer(pdf_bytes: bytes) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract text using pdfminer.six (most comprehensive).
    Returns (text, error).
    """
    try:
        from pdfminer.high_level import extract_text
    except ImportError:
        return None, "pdfminer.six not installed"

    try:
        text = extract_text(io.BytesIO(pdf_bytes))
        if text and len(text.strip()) > 0:
            return text, None
        return None, "No text extracted"

    except Exception as e:
        return None, str(e)


# ============================================================================
# Main Extraction Functions
# ============================================================================

def extract_pdf_text(
    pdf_bytes: bytes,
    method: Optional[str] = None,
    fallback: bool = True
) -> str:
    """
    Extract text from PDF bytes.

    Args:
        pdf_bytes: Raw PDF content as bytes
        method: Specific method to use ('pdfplumber', 'pypdf2', 'pdfminer')
                If None, tries all methods
        fallback: If True, try other methods if preferred fails

    Returns:
        Extracted text or empty string if extraction fails
    """
    methods = []

    if method:
        if method == "pdfplumber":
            methods = [extract_with_pdfplumber]
        elif method == "pypdf2":
            methods = [extract_with_pypdf2]
        elif method == "pdfminer":
            methods = [extract_with_pdfminer]
    else:
        # Default order: pdfplumber first (best for complex layouts)
        methods = [
            extract_with_pdfplumber,
            extract_with_pypdf2,
            extract_with_pdfminer,
        ]

    if not fallback:
        methods = methods[:1]

    errors = []
    for extract_fn in methods:
        text, error = extract_fn(pdf_bytes)
        if text and len(text.strip()) > 50:  # Minimum viable content
            return clean_extracted_text(text)
        if error:
            errors.append(f"{extract_fn.__name__}: {error}")

    # All methods failed
    if errors:
        log(f"PDF extraction failed: {'; '.join(errors)}")

    return ""


def extract_pdf_text_from_file(file_path: str) -> str:
    """Extract text from a PDF file."""
    with open(file_path, "rb") as f:
        return extract_pdf_text(f.read())


def extract_pdf_text_from_url(url: str, timeout: int = 60) -> str:
    """
    Extract text from a PDF at a URL.

    Args:
        url: URL to the PDF file
        timeout: Request timeout in seconds

    Returns:
        Extracted text or empty string
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Short Gravity Research"
        }
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, timeout=timeout) as response:
            pdf_bytes = response.read()

        return extract_pdf_text(pdf_bytes)

    except Exception as e:
        log(f"Error fetching PDF from {url}: {e}")
        return ""


# ============================================================================
# Text Cleaning
# ============================================================================

def clean_extracted_text(text: str) -> str:
    """
    Clean up extracted PDF text.

    - Normalize whitespace
    - Remove common PDF artifacts
    - Fix broken words from line breaks
    """
    import re

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove form feed characters
    text = text.replace("\f", "\n\n")

    # Remove null characters
    text = text.replace("\x00", "")

    # Fix hyphenated line breaks (word-\nbreak -> wordbreak)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Normalize multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Normalize multiple spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove leading/trailing whitespace from lines
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Remove empty lines at start/end
    text = text.strip()

    return text


# ============================================================================
# Metadata Extraction
# ============================================================================

def extract_pdf_metadata(pdf_bytes: bytes) -> Dict:
    """
    Extract metadata from PDF (title, author, creation date, etc.).

    Returns dict with available metadata fields.
    """
    metadata = {
        "page_count": 0,
        "title": None,
        "author": None,
        "subject": None,
        "creator": None,
        "producer": None,
        "creation_date": None,
        "modification_date": None,
    }

    # Try PyPDF2 first
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))

        metadata["page_count"] = len(reader.pages)

        if reader.metadata:
            metadata["title"] = reader.metadata.get("/Title")
            metadata["author"] = reader.metadata.get("/Author")
            metadata["subject"] = reader.metadata.get("/Subject")
            metadata["creator"] = reader.metadata.get("/Creator")
            metadata["producer"] = reader.metadata.get("/Producer")
            # Dates are often in format D:YYYYMMDDHHmmss
            metadata["creation_date"] = reader.metadata.get("/CreationDate")
            metadata["modification_date"] = reader.metadata.get("/ModDate")

        return metadata

    except ImportError:
        pass
    except Exception as e:
        log(f"Error extracting metadata with PyPDF2: {e}")

    # Try pdfplumber as fallback
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            metadata["page_count"] = len(pdf.pages)
            if pdf.metadata:
                metadata.update({
                    k.lower().replace("/", ""): v
                    for k, v in pdf.metadata.items()
                    if v is not None
                })
        return metadata

    except ImportError:
        pass
    except Exception as e:
        log(f"Error extracting metadata with pdfplumber: {e}")

    return metadata


# ============================================================================
# FCC-specific helpers
# ============================================================================

def extract_fcc_filing_text(pdf_bytes: bytes) -> Dict:
    """
    Extract text and metadata from an FCC filing PDF.

    Returns dict with:
        - text: Extracted text content
        - metadata: PDF metadata
        - page_count: Number of pages
        - char_count: Character count
    """
    text = extract_pdf_text(pdf_bytes)
    metadata = extract_pdf_metadata(pdf_bytes)

    return {
        "text": text,
        "metadata": metadata,
        "page_count": metadata.get("page_count", 0),
        "char_count": len(text),
    }


# ============================================================================
# CLI
# ============================================================================

def main():
    """Command-line interface."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract text from PDF files")
    parser.add_argument("input", help="PDF file path or URL")
    parser.add_argument("--method", choices=["pdfplumber", "pypdf2", "pdfminer"],
                       help="Extraction method to use")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--metadata", "-m", action="store_true",
                       help="Also print metadata")

    args = parser.parse_args()

    # Determine input type
    if args.input.startswith("http://") or args.input.startswith("https://"):
        log(f"Fetching PDF from URL: {args.input}")
        text = extract_pdf_text_from_url(args.input)
        if args.metadata:
            # Need to refetch for metadata
            try:
                headers = {"User-Agent": "Short Gravity Research"}
                req = urllib.request.Request(args.input, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as response:
                    pdf_bytes = response.read()
                metadata = extract_pdf_metadata(pdf_bytes)
            except:
                metadata = {}
    else:
        if not os.path.exists(args.input):
            log(f"Error: File not found: {args.input}")
            sys.exit(1)

        log(f"Reading PDF from file: {args.input}")
        with open(args.input, "rb") as f:
            pdf_bytes = f.read()

        text = extract_pdf_text(pdf_bytes, method=args.method)
        metadata = extract_pdf_metadata(pdf_bytes) if args.metadata else {}

    if not text:
        log("Error: No text could be extracted from PDF")
        sys.exit(1)

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            if args.metadata:
                f.write(f"=== METADATA ===\n{json.dumps(metadata, indent=2, default=str)}\n\n")
            f.write(text)
        log(f"Output written to: {args.output}")
    else:
        if args.metadata:
            import json
            print("=== METADATA ===")
            print(json.dumps(metadata, indent=2, default=str))
            print("\n=== TEXT ===")
        print(text)

    log(f"Extracted {len(text):,} characters from {metadata.get('page_count', '?')} pages")


if __name__ == "__main__":
    main()
