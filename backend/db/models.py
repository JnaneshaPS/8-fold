from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pydantic import BaseModel, Field

from .client import Base


class Persona(Base):
    __tablename__ = "personas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(100))
    company: Mapped[Optional[str]] = mapped_column(String(200))
    region: Mapped[Optional[str]] = mapped_column(String(100))
    goal: Mapped[Optional[str]] = mapped_column(String(300))
    notes: Mapped[Optional[str]] = mapped_column(String(1000))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    reports: Mapped[list["Report"]] = relationship(
        back_populates="persona",
        cascade="all, delete-orphan",
    )
    compare_sessions: Mapped[list["CompareSession"]] = relationship(
        back_populates="persona",
        cascade="all, delete-orphan",
    )


class Report(Base):
    """
    A full research output for a (persona, company).
    Stores the entire JSON of all sections.
    """

    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
    )

    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_website: Mapped[Optional[str]] = mapped_column(String(300))
    company_hq: Mapped[Optional[str]] = mapped_column(String(200))

    report_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_viewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    persona: Mapped["Persona"] = relationship(back_populates="reports")

    __table_args__ = (
        UniqueConstraint(
            "persona_id", "company_name", "created_at",
            name="uq_report_persona_company_created",
        ),
    )


class CompareSession(Base):
    """
    A comparison between two companies for a persona.

    The compare agent is responsible for:
    - extracting company_a_name and company_b_name from the user's query
      (or asking 'compare against what?' if missing),
    - producing comparison_json.

    """

    __tablename__ = "compare_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
    )

    original_query: Mapped[str] = mapped_column(String(1000), nullable=False)
    company_a_name: Mapped[str] = mapped_column(String(200), nullable=False)
    company_b_name: Mapped[str] = mapped_column(String(200), nullable=False)

    comparison_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    persona: Mapped["Persona"] = relationship(back_populates="compare_sessions")


class PersonaCreate(BaseModel):
    name: str
    role: Optional[str] = None
    company: Optional[str] = None
    region: Optional[str] = None
    goal: Optional[str] = None
    notes: Optional[str] = None


class PersonaRead(BaseModel):
    id: uuid.UUID
    name: str
    role: Optional[str]
    company: Optional[str]
    region: Optional[str]
    goal: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportCreate(BaseModel):
    persona_id: uuid.UUID
    company_name: str
    company_website: Optional[str] = None
    company_hq: Optional[str] = None
    report_json: dict[str, Any]


class ReportRead(BaseModel):
    id: uuid.UUID
    persona_id: uuid.UUID
    company_name: str
    company_website: Optional[str]
    company_hq: Optional[str]
    report_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_viewed_at: Optional[datetime]

    class Config:
        from_attributes = True


class CompareSessionCreate(BaseModel):
    persona_id: uuid.UUID
    original_query: str
    company_a_name: str
    company_b_name: str
    comparison_json: dict[str, Any] = Field(default_factory=dict)


class CompareSessionRead(BaseModel):
    id: uuid.UUID
    persona_id: uuid.UUID
    original_query: str
    company_a_name: str
    company_b_name: str
    comparison_json: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
