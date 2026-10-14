"""
Tests for document ingestion, deterministic chunking, and error recovery.
"""

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.models.models import Document
from app.services.document_service import (
    index_document,
    make_deterministic_chunk_id,
    reconcile_documents,
    split_text,
)


def test_deterministic_chunk_id_is_reproducible():
    doc_id = uuid.uuid4()
    # Same inputs must produce the identical UUID
    id1 = make_deterministic_chunk_id(doc_id, page_number=1, chunk_index=0, version=1)
    id2 = make_deterministic_chunk_id(doc_id, page_number=1, chunk_index=0, version=1)
    assert id1 == id2
    # Valid UUID string format
    assert uuid.UUID(id1)

    # Different chunk index produces different ID
    id3 = make_deterministic_chunk_id(doc_id, page_number=1, chunk_index=1, version=1)
    assert id1 != id3

    # Different version produces different ID
    id4 = make_deterministic_chunk_id(doc_id, page_number=1, chunk_index=0, version=2)
    assert id1 != id4


def test_split_text_chunks_correctly():
    text = "Word " * 250
    chunks = split_text(text)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 800


def test_index_document_fails_cleanly_on_empty_text_pdf(tmp_path):
    # Mock PdfReader to return page with empty text (e.g. scanned image without OCR)
    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    doc = Document(
        id=uuid.uuid4(),
        filename="scanned.pdf",
        stored_path=str(tmp_path / "scanned.pdf"),
        status="uploaded",
        chunk_count=0,
    )
    mock_db = MagicMock()

    with patch("app.services.document_service.ensure_collection"), \
         patch("app.services.document_service.PdfReader", return_value=mock_reader):
        with pytest.raises(ValueError) as excinfo:
            index_document(mock_db, doc, tmp_path / "scanned.pdf")

    assert "No extractable text found" in str(excinfo.value)
    assert doc.status == "failed"
    assert "No extractable text" in doc.error_message


def test_reprocessing_document_upserts_same_chunk_ids(tmp_path):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Policy section A content. Policy section B content."
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        filename="test.pdf",
        stored_path=str(tmp_path / "test.pdf"),
        status="uploaded",
        chunk_count=0,
        version=1,
    )
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = []

    captured_points_run1 = []
    captured_points_run2 = []

    def mock_upsert_1(collection_name, points, wait):
        captured_points_run1.extend(points)

    def mock_upsert_2(collection_name, points, wait):
        captured_points_run2.extend(points)

    with patch("app.services.document_service.ensure_collection"), \
         patch("app.services.document_service.PdfReader", return_value=mock_reader), \
         patch("app.services.document_service.qdrant.upsert", side_effect=mock_upsert_1):
        index_document(mock_db, doc, tmp_path / "test.pdf")

    with patch("app.services.document_service.ensure_collection"), \
         patch("app.services.document_service.PdfReader", return_value=mock_reader), \
         patch("app.services.document_service.qdrant.upsert", side_effect=mock_upsert_2):
        index_document(mock_db, doc, tmp_path / "test.pdf")

    # IDs between run 1 and run 2 must match exactly -> zero duplicate vectors in Qdrant!
    ids_1 = [p.id for p in captured_points_run1]
    ids_2 = [p.id for p in captured_points_run2]
    assert ids_1 == ids_2
    assert len(ids_1) > 0


def test_reconcile_documents_flags_orphaned_or_missing_vectors():
    mock_db = MagicMock()
    doc_missing = Document(id=uuid.uuid4(), status="indexed", filename="doc1.pdf")
    doc_failed_with_vectors = Document(id=uuid.uuid4(), status="failed", filename="doc2.pdf")
    mock_db.scalars.return_value.all.return_value = [doc_missing, doc_failed_with_vectors]

    # Return 0 vectors for indexed doc (missing), and 5 vectors for failed doc (orphaned)
    mock_count_1 = MagicMock(count=0)
    mock_count_2 = MagicMock(count=5)

    with patch("app.services.document_service.ensure_collection"), \
         patch("app.services.document_service.qdrant.count", side_effect=[mock_count_1, mock_count_2]):
        report = reconcile_documents(mock_db)

    assert report["total_documents"] == 2
    assert report["inconsistencies_found"] == 2
    issues = [item["action_required"] for item in report["inconsistencies"]]
    assert "reindex" in issues
    assert "cleanup_vectors" in issues
