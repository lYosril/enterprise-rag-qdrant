import logging

logger = logging.getLogger(__name__)

import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.models import Conversation, Document, Message, User
from app.schemas.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    DocumentResponse,
    MessageResponse,
    SourceResponse,
)
from app.services.document_service import (
    DOCUMENT_DIR,
    delete_document_vectors,
    index_document,
)
from app.services.rag_service import answer_question


router = APIRouter(prefix="/api/v1")


@router.post(
    "/documents/upload",
    response_model=DocumentResponse,
)
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported.",
        )

    DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

    document_id = uuid.uuid4()
    saved_path = DOCUMENT_DIR / f"{document_id}.pdf"

    document = Document(
        id=document_id,
        filename=Path(file.filename).name,
        stored_path=str(saved_path),
        status="processing",
        chunk_count=0,
        owner_id=current_user.id,
    )

    try:
        # Limit upload size to 20 MB.
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)

        if size > 20 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="PDF must be 20 MB or smaller.",
            )

        with saved_path.open("wb") as output:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)

        db.add(document)
        db.commit()
        db.refresh(document)

        index_document(db, document, saved_path)

        return document

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()

        # Best-effort cleanup of any partially indexed vectors.
        try:
            delete_document_vectors(document_id)
        except Exception:
            pass

        db_document = db.get(Document, document_id)
        if db_document:
            db.delete(db_document)
            db.commit()

        saved_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail=f"Document ingestion failed: {exc}",
        ) from exc
    finally:
        file.file.close()


@router.get(
    "/documents",
    response_model=list[DocumentResponse],
)
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Document)
        .where(Document.owner_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    return list(db.scalars(statement).all())


@router.delete("/documents/{document_id}")
def remove_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    try:
        delete_document_vectors(document_id)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not remove document vectors.",
        ) from exc

    saved_path = Path(document.stored_path)

    db.delete(document)
    db.commit()

    saved_path.unlink(missing_ok=True)

    return {"message": "Document deleted successfully."}


@router.get(
    "/conversations",
    response_model=list[ConversationResponse],
)
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = (
        select(Conversation)
        .where(Conversation.owner_id == current_user.id)
        .order_by(Conversation.created_at.desc())
    )
    return list(db.scalars(statement).all())


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
def list_conversation_messages(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.owner_id == current_user.id,
        )
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="Question cannot be empty.",
        )

    if request.conversation_id:
        conversation = db.scalar(
            select(Conversation).where(
                Conversation.id == request.conversation_id,
                Conversation.owner_id == current_user.id,
            )
        )

        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )
    else:
        conversation = Conversation(owner_id=current_user.id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    try:
        result = answer_question(
            question,
            owner_id=str(current_user.id),
        )
    except Exception as exc:
        logger.exception("RAG chat request failed")

        raise HTTPException(
            status_code=502,
            detail="The RAG service failed to generate an answer.",
        ) from exc

    db.add_all([
        Message(
            conversation_id=conversation.id,
            role="user",
            content=question,
            sources=[],
        ),
        Message(
            conversation_id=conversation.id,
            role="assistant",
            content=result["answer"],
            sources=result["sources"],
        ),
    ])
    db.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        answer=result["answer"],
        sources=[
            SourceResponse(**source)
            for source in result["sources"]
        ],
    )
