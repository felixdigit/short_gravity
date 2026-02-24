#!/usr/bin/env python3
"""
Supabase Storage Utilities

Provides functions for uploading/downloading documents to Supabase Storage.
Used by SEC and FCC filing workers for full document preservation.
"""

import hashlib
import json
import os
import urllib.request
import urllib.error
from typing import Optional, Tuple
from datetime import datetime


# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Storage buckets
SEC_BUCKET = "sec-filings"
FCC_BUCKET = "fcc-filings"


def log(msg: str):
    """Print with timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def compute_hash(content: str | bytes) -> str:
    """Compute SHA-256 hash of content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _storage_request(
    method: str,
    bucket: str,
    path: str,
    data: Optional[bytes] = None,
    content_type: str = "text/plain",
) -> Tuple[int, bytes]:
    """Make Supabase Storage REST API request."""
    if not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_KEY not set")

    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": content_type,
    }

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def upload_document(
    bucket: str,
    path: str,
    content: str | bytes,
    content_type: str = "text/plain; charset=utf-8",
    upsert: bool = True,
) -> dict:
    """
    Upload document to Supabase Storage.

    Args:
        bucket: Storage bucket name (sec-filings, fcc-filings)
        path: Path within bucket (e.g., "10-K/0001780312-24-000001.txt")
        content: Document content (string or bytes)
        content_type: MIME type of content
        upsert: If True, overwrite existing file

    Returns:
        dict with 'success', 'path', 'hash', 'size'
    """
    if isinstance(content, str):
        data = content.encode("utf-8")
    else:
        data = content

    content_hash = compute_hash(data)
    size = len(data)

    # Use POST for new files, PUT for upsert
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": content_type,
    }

    if upsert:
        headers["x-upsert"] = "true"

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            return {
                "success": True,
                "path": path,
                "hash": content_hash,
                "size": size,
                "key": result.get("Key"),
            }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"Storage upload error: {e.code} - {error_body}")
        return {
            "success": False,
            "error": f"{e.code}: {error_body}",
            "path": path,
        }


def download_document(bucket: str, path: str) -> Optional[bytes]:
    """
    Download document from Supabase Storage.

    Args:
        bucket: Storage bucket name
        path: Path within bucket

    Returns:
        Document content as bytes, or None if not found
    """
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }

    req = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def file_exists(bucket: str, path: str) -> bool:
    """Check if file exists in storage."""
    url = f"{SUPABASE_URL}/storage/v1/object/info/{bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }

    req = urllib.request.Request(url, headers=headers, method="HEAD")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except urllib.error.HTTPError:
        return False


def delete_document(bucket: str, path: str) -> bool:
    """Delete document from storage."""
    url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }

    req = urllib.request.Request(url, headers=headers, method="DELETE")

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status == 200
    except urllib.error.HTTPError:
        return False


def list_files(bucket: str, prefix: str = "", limit: int = 100) -> list:
    """
    List files in storage bucket with optional prefix.

    Args:
        bucket: Storage bucket name
        prefix: Path prefix to filter by
        limit: Maximum number of files to return

    Returns:
        List of file info dicts
    """
    url = f"{SUPABASE_URL}/storage/v1/object/list/{bucket}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    body = json.dumps({
        "prefix": prefix,
        "limit": limit,
        "sortBy": {"column": "created_at", "order": "desc"},
    }).encode()

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        log(f"List files error: {e.code}")
        return []


def get_public_url(bucket: str, path: str) -> str:
    """Get public URL for a file (if bucket is public)."""
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"


def get_signed_url(bucket: str, path: str, expires_in: int = 3600) -> Optional[str]:
    """
    Get signed URL for private file access.

    Args:
        bucket: Storage bucket name
        path: Path within bucket
        expires_in: URL expiration time in seconds (default 1 hour)

    Returns:
        Signed URL string or None on error
    """
    url = f"{SUPABASE_URL}/storage/v1/object/sign/{bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

    body = json.dumps({"expiresIn": expires_in}).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return f"{SUPABASE_URL}/storage/v1{result['signedURL']}"
    except urllib.error.HTTPError as e:
        log(f"Signed URL error: {e.code}")
        return None


# ============================================================================
# SEC-specific helpers
# ============================================================================

def upload_sec_filing(
    accession_number: str,
    form_type: str,
    content: str,
    document_name: str = "primary.txt",
) -> dict:
    """
    Upload SEC filing to storage with standardized path.

    Path format: {form_type}/{accession_number}/{document_name}
    Example: 10-K/0001780312-24-000001/primary.txt
    """
    # Normalize form type for path (remove slashes and spaces)
    form_path = form_type.replace("/", "-").replace(" ", "_")
    path = f"{form_path}/{accession_number}/{document_name}"

    return upload_document(SEC_BUCKET, path, content)


def upload_sec_exhibit(
    accession_number: str,
    exhibit_number: str,
    content: str | bytes,
    content_type: str = "text/html",
) -> dict:
    """
    Upload SEC exhibit to storage.

    Path format: exhibits/{accession_number}/{exhibit_number}
    Example: exhibits/0001780312-24-000001/EX-10.1.htm
    """
    # Normalize exhibit number for filename
    exhibit_file = exhibit_number.replace(" ", "-")
    path = f"exhibits/{accession_number}/{exhibit_file}"

    return upload_document(SEC_BUCKET, path, content, content_type)


# ============================================================================
# FCC-specific helpers
# ============================================================================

def upload_fcc_filing(
    filing_system: str,
    file_number: str,
    content: str | bytes,
    filename: str = "filing.txt",
    content_type: str = "text/plain; charset=utf-8",
) -> dict:
    """
    Upload FCC filing to storage with standardized path.

    Path format: {filing_system}/{file_number}/{filename}
    Example: icfs/SAT-LOA-20200727-00088/filing.pdf
    """
    # Normalize file number for path
    safe_file_number = file_number.replace("/", "-")
    path = f"{filing_system.lower()}/{safe_file_number}/{filename}"

    return upload_document(FCC_BUCKET, path, content, content_type)


def upload_fcc_attachment(
    file_number: str,
    attachment_number: int,
    content: bytes,
    filename: str,
    content_type: str = "application/pdf",
) -> dict:
    """
    Upload FCC filing attachment to storage.

    Path format: attachments/{file_number}/{attachment_number}_{filename}
    """
    safe_file_number = file_number.replace("/", "-")
    safe_filename = filename.replace(" ", "_")
    path = f"attachments/{safe_file_number}/{attachment_number:02d}_{safe_filename}"

    return upload_document(FCC_BUCKET, path, content, content_type)


# ============================================================================
# Test
# ============================================================================

if __name__ == "__main__":
    # Test storage utilities
    log("Testing storage utilities...")

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        log("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        exit(1)

    # Test hash computation
    test_content = "Hello, world!"
    test_hash = compute_hash(test_content)
    log(f"Hash of '{test_content}': {test_hash[:16]}...")

    # Test upload (dry run - would need bucket created first)
    log("Storage utilities ready.")
    log("Note: Run migration 006_filing_storage.sql and create buckets before use.")
