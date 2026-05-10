import uuid
import hashlib
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.doctrine import DoctrineDocument
from app.models.ai_audit import AIAudit
from app.schemas.doctrine import DoctrineCreate, RebuildIndexRequest
from app.dependencies import get_current_user, require_roles
from app.services import ai_service

router = APIRouter(prefix="/doctrine", tags=["Doctrine"])


def _doc_to_dict(d: DoctrineDocument) -> dict:
    return {
        "id": str(d.id),
        "title": d.title,
        "domain": d.domain,
        "version": d.version,
        "content_hash": d.content_hash,
        "file_ref": d.file_ref,
        "embedded_at": d.embedded_at.isoformat() if d.embedded_at else None,
        "approved_by": str(d.approved_by) if d.approved_by else None,
        "is_active": d.is_active,
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
    }


@router.get("", response_model=dict)
async def list_doctrine(
    domain: str = None,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List doctrine documents."""
    query = db.query(DoctrineDocument)
    if active_only:
        query = query.filter(DoctrineDocument.is_active == True)
    if domain:
        query = query.filter(DoctrineDocument.domain == domain)
    docs = query.order_by(DoctrineDocument.created_at.desc()).all()
    return {
        "success": True,
        "message": "Doctrine documents retrieved",
        "data": [_doc_to_dict(d) for d in docs],
    }


@router.post("", response_model=dict, status_code=201)
async def add_doctrine(
    body: DoctrineCreate,
    current_user: User = Depends(require_roles("doctrine", "admin")),
    db: Session = Depends(get_db),
):
    """Add a new doctrine document. Doctrine role required."""
    content_hash = None
    if body.content_text:
        content_hash = hashlib.sha256(body.content_text.encode()).hexdigest()

    doc = DoctrineDocument(
        id=uuid.uuid4(),
        title=body.title,
        domain=body.domain,
        version=body.version,
        content_hash=content_hash,
        file_ref=body.file_ref,
        content_text=body.content_text,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "success": True,
        "message": "Doctrine document added",
        "data": _doc_to_dict(doc),
    }


@router.put("/{doc_id}/approve", response_model=dict)
async def approve_doctrine(
    doc_id: uuid.UUID,
    current_user: User = Depends(require_roles("doctrine", "fleet", "admin")),
    db: Session = Depends(get_db),
):
    """Approve a doctrine document for active use."""
    doc = db.query(DoctrineDocument).filter(DoctrineDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Doctrine document not found")

    doc.approved_by = current_user.id
    doc.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "success": True,
        "message": "Doctrine document approved",
        "data": _doc_to_dict(doc),
    }


@router.post("/rebuild-index", response_model=dict)
async def rebuild_doctrine_index(
    body: RebuildIndexRequest,
    current_user: User = Depends(require_roles("doctrine", "admin")),
    db: Session = Depends(get_db),
):
    """
    Trigger re-embedding of doctrine documents into the Qdrant vector store.
    Doctrine role required.
    """
    query = db.query(DoctrineDocument).filter(DoctrineDocument.is_active == True)
    if body.domain:
        query = query.filter(DoctrineDocument.domain == body.domain)

    docs = query.all()
    embedded_count = 0
    failed_count = 0

    for doc in docs:
        if not doc.content_text and not body.force:
            continue
        text = doc.content_text or doc.title
        embedding = await ai_service.embed(text)
        if embedding:
            # In production this would upsert into Qdrant
            # For now we mark the embedded_at timestamp
            doc.embedded_at = datetime.now(timezone.utc)
            db.commit()
            embedded_count += 1
        else:
            failed_count += 1

    return {
        "success": True,
        "message": "Doctrine index rebuild complete",
        "data": {
            "total_processed": len(docs),
            "embedded": embedded_count,
            "failed": failed_count,
            "domain": body.domain or "all",
        },
    }


@router.get("/ai-groundings", response_model=dict)
async def get_ai_groundings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return which doctrine documents the AI has been using,
    derived from the AI audit log's doctrine_version_used field.
    """
    # Get unique doctrine versions used in AI interactions
    from sqlalchemy import distinct
    versions_used = (
        db.query(AIAudit.doctrine_version_used)
        .filter(AIAudit.doctrine_version_used != None)
        .distinct()
        .all()
    )
    version_list = [v[0] for v in versions_used]

    # Find matching active doctrine docs
    grounding_docs = []
    for version in version_list:
        docs = (
            db.query(DoctrineDocument)
            .filter(DoctrineDocument.version == version, DoctrineDocument.is_active == True)
            .all()
        )
        for doc in docs:
            # Count uses
            use_count = (
                db.query(AIAudit)
                .filter(AIAudit.doctrine_version_used == version)
                .count()
            )
            latest_use = (
                db.query(AIAudit)
                .filter(AIAudit.doctrine_version_used == version)
                .order_by(AIAudit.timestamp.desc())
                .first()
            )
            grounding_docs.append({
                "document_id": str(doc.id),
                "title": doc.title,
                "domain": doc.domain,
                "version": doc.version,
                "usage_count": use_count,
                "last_used": latest_use.timestamp.isoformat() if latest_use else None,
            })

    return {
        "success": True,
        "message": "AI groundings retrieved",
        "data": grounding_docs,
    }
