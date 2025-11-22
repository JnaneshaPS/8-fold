from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .client import Base, engine
from .models import (
    Persona,
    PersonaCreate,
    PersonaRead,
    Report,
    ReportCreate,
    ReportRead,
    CompareSession,
    CompareSessionCreate,
    CompareSessionRead,
)


def init_db() -> None:
    """
    Create tables if they don't exist.

    Call this once at startup (e.g., from app.py) for now.
    Later you can switch to Alembic migrations.
    """
    Base.metadata.create_all(bind=engine)


def create_persona(db: Session, data: PersonaCreate) -> PersonaRead:
    """
    Insert a new Persona row and return it as a Pydantic PersonaRead.
    """
    persona = Persona(
        name=data.name,
        role=data.role,
        company=data.company,
        region=data.region,
        goal=data.goal,
        notes=data.notes,
    )
    db.add(persona)
    db.flush()
    db.refresh(persona)
    return PersonaRead.model_validate(persona)


def list_personas(db: Session) -> List[PersonaRead]:
    """
    List all personas ordered by creation time (newest first).
    """
    stmt = select(Persona).order_by(Persona.created_at.desc())
    rows = db.execute(stmt).scalars().all()
    return [PersonaRead.model_validate(p) for p in rows]


def get_persona(db: Session, persona_id: uuid.UUID) -> Optional[PersonaRead]:
    """
    Fetch a single Persona by id.
    """
    persona = db.get(Persona, persona_id)
    if not persona:
        return None
    return PersonaRead.model_validate(persona)


def create_report(db: Session, data: ReportCreate) -> ReportRead:
    """
    Insert a new Report row with the full research JSON.
    """
    report = Report(
        persona_id=data.persona_id,
        company_name=data.company_name,
        company_website=data.company_website,
        company_hq=data.company_hq,
        report_json=data.report_json,
    )
    db.add(report)
    db.flush()
    db.refresh(report)
    return ReportRead.model_validate(report)


def list_reports_for_persona(db: Session, persona_id: uuid.UUID) -> List[ReportRead]:
    """
    List all reports for a given persona, newest first.
    """
    stmt = (
        select(Report)
        .where(Report.persona_id == persona_id)
        .order_by(Report.created_at.desc())
    )
    rows = db.execute(stmt).scalars().all()
    return [ReportRead.model_validate(r) for r in rows]


def get_latest_report_for_persona_company(
    db: Session,
    persona_id: uuid.UUID,
    company_name: str,
) -> Optional[ReportRead]:
    """
    Get the latest report for (persona, company_name), case-insensitive on name.
    Returns None if nothing exists.
    """
    stmt = (
        select(Report)
        .where(
            Report.persona_id == persona_id,
            Report.company_name.ilike(company_name),
        )
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    row = db.execute(stmt).scalars().first()
    if not row:
        return None
    return ReportRead.model_validate(row)


def touch_report_last_viewed(db: Session, report_id: uuid.UUID) -> None:
    """
    Update last_viewed_at timestamp for a report.
    Safe to call even if the report doesn't exist.
    """
    from datetime import datetime, timezone

    report = db.get(Report, report_id)
    if not report:
        return
    report.last_viewed_at = datetime.now(tz=timezone.utc)
    db.add(report)
    db.flush()


def create_compare_session(
    db: Session,
    data: CompareSessionCreate,
) -> CompareSessionRead:
    """
    Insert a new CompareSession.

    The compare agent is expected to:
    - parse the user's query,
    - extract company_a_name and company_b_name,
    - generate comparison_json.
    """
    obj = CompareSession(
        persona_id=data.persona_id,
        original_query=data.original_query,
        company_a_name=data.company_a_name,
        company_b_name=data.company_b_name,
        comparison_json=data.comparison_json,
    )
    db.add(obj)
    db.flush()
    db.refresh(obj)
    return CompareSessionRead.model_validate(obj)


def get_compare_session(
    db: Session,
    compare_id: uuid.UUID,
) -> Optional[CompareSessionRead]:
    """
    Fetch a CompareSession by id.
    """
    obj = db.get(CompareSession, compare_id)
    if not obj:
        return None
    return CompareSessionRead.model_validate(obj)
