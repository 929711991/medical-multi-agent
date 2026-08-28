from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    demo_label: Mapped[str] = mapped_column(String(120), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    data_scope: Mapped[str] = mapped_column(String(20), nullable=False, default="demo", index=True)
    source_channel: Mapped[str] = mapped_column(String(32), nullable=False, default="doctor_web", index=True)


class Doctor(Base, TimestampMixin):
    __tablename__ = "doctors"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    demo_name: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)


class MedicalVisit(Base):
    __tablename__ = "medical_visits"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    visit_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    department: Mapped[str] = mapped_column(String(120))
    chief_complaint: Mapped[str] = mapped_column(Text)
    record_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    test_name: Mapped[str] = mapped_column(String(160))
    value: Mapped[str] = mapped_column(String(160))
    reference_range: Mapped[str | None] = mapped_column(String(160), nullable=True)
    abnormal_flag: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ImagingReport(Base):
    __tablename__ = "imaging_reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    modality: Mapped[str] = mapped_column(String(80))
    body_part: Mapped[str] = mapped_column(String(120))
    findings: Mapped[str] = mapped_column(Text)
    impression: Mapped[str] = mapped_column(Text)


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    dose: Mapped[str | None] = mapped_column(String(100), nullable=True)
    route: Mapped[str | None] = mapped_column(String(80), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Allergy(Base):
    __tablename__ = "allergies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    substance: Mapped[str] = mapped_column(String(160))
    reaction: Mapped[str | None] = mapped_column(String(240), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MedicalCase(Base, TimestampMixin):
    __tablename__ = "medical_cases"
    __table_args__ = (Index("ix_medical_cases_thread_id", "thread_id", unique=True),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", index=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source_channel: Mapped[str] = mapped_column(String(32), nullable=False, default="doctor_web", index=True)
    assessments: Mapped[list["MedicalAssessment"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class MedicalAssessment(Base, TimestampMixin):
    __tablename__ = "medical_assessments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("medical_cases.id"), unique=True, index=True)
    ai_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    doctor_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), default="PENDING")
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[str | None] = mapped_column(ForeignKey("doctors.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    case: Mapped[MedicalCase] = relationship(back_populates="assessments")


class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", index=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
