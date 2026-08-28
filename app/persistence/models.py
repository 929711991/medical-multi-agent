from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    JSON,
    Date,
    DateTime,
    FetchedValue,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.snowflake import generate_snowflake_id


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """为业务表统一增加可审计的创建时间和更新时间。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="记录创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="记录最后更新时间",
    )


class AutoIdMixin:
    """为未来切换 ID 策略预留数据库自增列。"""

    # SQLAlchemy 仅会为主键渲染自增属性，因此由 initialize_schema 为该备用列补充自增定义。
    auto_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        server_default=FetchedValue(),
        comment="备用数据库自增编号",
    )


class Patient(AutoIdMixin, Base, TimestampMixin):
    __tablename__ = "patients"
    __table_args__ = {"comment": "患者主档表"}

    pk_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        default=generate_snowflake_id,
        autoincrement=False,
        comment="雪花算法内部主键",
    )
    id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        default=generate_snowflake_id,
        comment="患者业务编号",
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False, comment="患者显示姓名")
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="出生日期")
    sex: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="生理性别")
    summary_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, comment="患者病史与摘要信息"
    )
    data_scope: Mapped[str] = mapped_column(
        String(20), nullable=False, default="sandbox", index=True, comment="数据隔离范围"
    )
    source_channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="doctor_web",
        index=True,
        comment="患者数据来源渠道",
    )


class Doctor(AutoIdMixin, Base, TimestampMixin):
    __tablename__ = "doctors"
    __table_args__ = {"comment": "医生账号与执业信息表"}

    pk_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        default=generate_snowflake_id,
        autoincrement=False,
        comment="雪花算法内部主键",
    )
    id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        default=generate_snowflake_id,
        comment="医生业务编号",
    )
    account: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True, comment="医生登录账号"
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="PBKDF2 密码摘要"
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False, comment="医生姓名")
    department: Mapped[str] = mapped_column(String(120), nullable=False, comment="所属科室")
    title: Mapped[str | None] = mapped_column(String(120), nullable=True, comment="医生职称")


class Department(Base, TimestampMixin):
    __tablename__ = "departments"
    __table_args__ = {"comment": "接诊科室字典表"}

    pk_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        default=generate_snowflake_id,
        autoincrement=False,
        comment="雪花算法内部主键",
    )
    code: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, comment="稳定科室编码"
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False, comment="科室名称")
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False, comment="是否启用")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="显示顺序")


class MedicalVisit(AutoIdMixin, Base):
    __tablename__ = "medical_visits"
    __table_args__ = {"comment": "患者就诊记录表"}

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        default=generate_snowflake_id,
        autoincrement=False,
        comment="雪花算法主键",
    )
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id"), index=True, comment="患者编号"
    )
    visit_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, comment="就诊时间"
    )
    department: Mapped[str] = mapped_column(String(120), comment="接诊科室")
    department_code: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("departments.code"), nullable=True, index=True, comment="接诊科室稳定编码"
    )
    chief_complaint: Mapped[str] = mapped_column(Text, comment="患者主诉")
    record_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, comment="结构化病历内容")


class LabResult(AutoIdMixin, Base):
    __tablename__ = "lab_results"
    __table_args__ = {"comment": "患者检验结果表"}

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        default=generate_snowflake_id,
        autoincrement=False,
        comment="雪花算法主键",
    )
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id"), index=True, comment="患者编号"
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, comment="采样或观察时间"
    )
    test_name: Mapped[str] = mapped_column(String(160), comment="检验项目名称")
    value: Mapped[str] = mapped_column(String(160), comment="检验结果值")
    reference_range: Mapped[str | None] = mapped_column(
        String(160), nullable=True, comment="参考范围"
    )
    abnormal_flag: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="异常标记"
    )


class ImagingReport(AutoIdMixin, Base):
    __tablename__ = "imaging_reports"
    __table_args__ = {"comment": "患者影像检查报告表"}

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        default=generate_snowflake_id,
        autoincrement=False,
        comment="雪花算法主键",
    )
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id"), index=True, comment="患者编号"
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, comment="检查时间"
    )
    modality: Mapped[str] = mapped_column(String(80), comment="影像检查类型")
    body_part: Mapped[str] = mapped_column(String(120), comment="检查部位")
    findings: Mapped[str] = mapped_column(Text, comment="影像所见")
    impression: Mapped[str] = mapped_column(Text, comment="影像结论")


class Medication(AutoIdMixin, Base):
    __tablename__ = "medications"
    __table_args__ = {"comment": "患者用药记录表"}

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        default=generate_snowflake_id,
        autoincrement=False,
        comment="雪花算法主键",
    )
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id"), index=True, comment="患者编号"
    )
    name: Mapped[str] = mapped_column(String(160), comment="药品名称")
    dose: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="用药剂量")
    route: Mapped[str | None] = mapped_column(String(80), nullable=True, comment="给药途径")
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="开始用药时间"
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="停止用药时间"
    )


class Allergy(AutoIdMixin, Base):
    __tablename__ = "allergies"
    __table_args__ = {"comment": "患者过敏记录表"}

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        default=generate_snowflake_id,
        autoincrement=False,
        comment="雪花算法主键",
    )
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id"), index=True, comment="患者编号"
    )
    substance: Mapped[str] = mapped_column(String(160), comment="过敏原")
    reaction: Mapped[str | None] = mapped_column(
        String(240), nullable=True, comment="过敏反应"
    )
    severity: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="严重程度"
    )
    observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="记录或发生时间"
    )


class MedicalCase(AutoIdMixin, Base, TimestampMixin):
    __tablename__ = "medical_cases"
    __table_args__ = (
        Index("ix_medical_cases_thread_id", "thread_id", unique=True),
        {"comment": "AI 辅助诊断病例主表"},
    )

    pk_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        default=generate_snowflake_id,
        autoincrement=False,
        comment="雪花算法内部主键",
    )
    id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        default=generate_snowflake_id,
        comment="病例业务编号",
    )
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id"), index=True, comment="患者编号"
    )
    visit_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("medical_visits.id"), nullable=True, index=True, comment="本次接诊编号"
    )
    consultation_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True, comment="Consumer 咨询编号"
    )
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="诊断图线程编号")
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="医生提交的临床问题")
    status: Mapped[str] = mapped_column(
        String(32), default="CREATED", index=True, comment="病例处理状态"
    )
    risk_level: Mapped[str | None] = mapped_column(
        String(16), nullable=True, comment="风险等级"
    )
    source_channel: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="doctor_web",
        index=True,
        comment="病例创建渠道",
    )
    failure_stage: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="失败阶段"
    )
    error_code: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="机器可定位错误码"
    )
    assessments: Mapped[list["MedicalAssessment"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class MedicalAssessment(AutoIdMixin, Base, TimestampMixin):
    __tablename__ = "medical_assessments"
    __table_args__ = {"comment": "AI 评估与医生审核结果表"}

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        default=generate_snowflake_id,
        autoincrement=False,
        comment="雪花算法主键",
    )
    case_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("medical_cases.id"), unique=True, index=True, comment="病例编号"
    )
    ai_result_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="AI 原始评估结果"
    )
    doctor_result_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="医生最终审核结果"
    )
    review_status: Mapped[str] = mapped_column(
        String(32), default="PENDING", comment="审核状态"
    )
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审核说明")
    reviewer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("doctors.id"), nullable=True, comment="审核医生编号"
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="审核完成时间"
    )
    version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, comment="乐观锁版本号"
    )
    case: Mapped[MedicalCase] = relationship(back_populates="assessments")


class KnowledgeDocument(AutoIdMixin, Base, TimestampMixin):
    __tablename__ = "knowledge_documents"
    __table_args__ = {"comment": "RAG 医学知识文档索引表"}

    pk_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        default=generate_snowflake_id,
        autoincrement=False,
        comment="雪花算法内部主键",
    )
    id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        default=generate_snowflake_id,
        comment="知识文档编号",
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="文档标题")
    source: Mapped[str] = mapped_column(String(500), nullable=False, comment="文档来源")
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, comment="来源类型")
    version: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="文档版本")
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="发布日期"
    )
    checksum: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="内容校验和"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", index=True, comment="入库状态"
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="已切分知识块数量"
    )


class ConsumerUser(Base, TimestampMixin):
    __tablename__ = "consumer_users"
    __table_args__ = {"comment": "微信消费者账号表"}

    pk_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=generate_snowflake_id)
    id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True, default=generate_snowflake_id
    )
    openid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    unionid: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    nickname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", index=True)


class ConsumerPatientRelation(Base, TimestampMixin):
    __tablename__ = "consumer_patient_relations"
    __table_args__ = (
        UniqueConstraint("consumer_user_id", "patient_id", name="ux_consumer_patient_relation"),
        {"comment": "消费者与共享患者主档的授权关系"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=generate_snowflake_id)
    consumer_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("consumer_users.id"), nullable=False, index=True
    )
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    permission: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", index=True)
    invited_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("consumer_users.id"), nullable=True
    )


class Consultation(Base, TimestampMixin):
    __tablename__ = "consultations"
    __table_args__ = (Index("ix_consultations_thread_id", "thread_id", unique=True),)

    pk_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=generate_snowflake_id)
    id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, index=True, default=generate_snowflake_id
    )
    consumer_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("consumer_users.id"), nullable=False, index=True
    )
    patient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("patients.id"), nullable=False, index=True
    )
    thread_id: Mapped[str] = mapped_column(String(64), nullable=False)
    consultation_type: Mapped[str] = mapped_column(String(32), nullable=False, default="health_advice")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CREATED", index=True)
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    recommended_department_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    linked_case_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("medical_cases.id"), nullable=True, index=True
    )
    failure_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_channel: Mapped[str] = mapped_column(
        String(32), nullable=False, default="wechat_mini_program"
    )


class ConsultationMessage(Base):
    __tablename__ = "consultation_messages"
    __table_args__ = (
        UniqueConstraint("consultation_id", "client_message_id", name="ux_consultation_client_message"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=generate_snowflake_id)
    consultation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("consultations.id"), nullable=False, index=True
    )
    client_message_id: Mapped[str] = mapped_column(String(128), nullable=False)
    sender_type: Mapped[str] = mapped_column(String(32), nullable=False)
    sender_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConsultationShareGrant(Base):
    __tablename__ = "consultation_share_grants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=generate_snowflake_id)
    consultation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("consultations.id"), nullable=False, index=True
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("consumer_users.id"), nullable=False, index=True
    )
    share_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(20), nullable=False, default="VIEW")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConsultationAccessGrant(Base, TimestampMixin):
    __tablename__ = "consultation_access_grants"
    __table_args__ = (
        UniqueConstraint("consultation_id", "consumer_user_id", name="ux_consultation_access"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=generate_snowflake_id)
    consultation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("consultations.id"), nullable=False, index=True
    )
    consumer_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("consumer_users.id"), nullable=False, index=True
    )
    share_grant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("consultation_share_grants.id"), nullable=False, index=True
    )
    permission: Mapped[str] = mapped_column(String(20), nullable=False, default="VIEW")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")


class ConsumerConsentRecord(Base):
    __tablename__ = "consumer_consent_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, default=generate_snowflake_id)
    consumer_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("consumer_users.id"), nullable=False, index=True
    )
    agreement_type: Mapped[str] = mapped_column(String(64), nullable=False)
    agreement_version: Mapped[str] = mapped_column(String(32), nullable=False)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
