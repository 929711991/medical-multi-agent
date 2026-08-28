from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.identifiers import identifier_to_bigint
from app.core.snowflake import generate_snowflake_id
from app.persistence.models import (
    Consultation,
    ConsultationAccessGrant,
    ConsultationMessage,
    ConsultationShareGrant,
    ConsumerConsentRecord,
    ConsumerPatientRelation,
    ConsumerUser,
    Patient,
)


def _id(value: str | int, namespace: str) -> int:
    result = identifier_to_bigint(value, namespace=namespace)
    if result is None:
        raise ValueError(f"INVALID_{namespace.upper()}_ID")
    return result


class ConsumerUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: str | int) -> ConsumerUser | None:
        return await self.session.scalar(
            select(ConsumerUser).where(ConsumerUser.id == _id(user_id, "consumer_user"))
        )

    async def get_by_openid(self, openid: str) -> ConsumerUser | None:
        return await self.session.scalar(select(ConsumerUser).where(ConsumerUser.openid == openid))

    async def create_or_update(
        self, *, openid: str, unionid: str | None, nickname: str | None, avatar: str | None
    ) -> ConsumerUser:
        user = await self.get_by_openid(openid)
        if user is None:
            user = ConsumerUser(
                id=generate_snowflake_id(),
                openid=openid,
                unionid=unionid,
                nickname=nickname,
                avatar=avatar,
                status="ACTIVE",
            )
            self.session.add(user)
        else:
            user.unionid = unionid or user.unionid
            user.nickname = nickname if nickname is not None else user.nickname
            user.avatar = avatar if avatar is not None else user.avatar
        await self.session.commit()
        await self.session.refresh(user)
        return user


class ConsumerPatientRelationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: str | int, patient_id: str | int) -> ConsumerPatientRelation | None:
        return await self.session.scalar(
            select(ConsumerPatientRelation).where(
                ConsumerPatientRelation.consumer_user_id == _id(user_id, "consumer_user"),
                ConsumerPatientRelation.patient_id == _id(patient_id, "patient"),
                ConsumerPatientRelation.status == "ACTIVE",
            )
        )

    async def create(
        self,
        *,
        user_id: str | int,
        patient_id: str | int,
        relation_type: str,
        permission: str,
        invited_by: str | int | None = None,
        commit: bool = True,
    ) -> ConsumerPatientRelation:
        relation = ConsumerPatientRelation(
            consumer_user_id=_id(user_id, "consumer_user"),
            patient_id=_id(patient_id, "patient"),
            relation_type=relation_type,
            permission=permission,
            invited_by=_id(invited_by, "consumer_user") if invited_by is not None else None,
            status="ACTIVE",
        )
        self.session.add(relation)
        if commit:
            await self.session.commit()
            await self.session.refresh(relation)
        else:
            await self.session.flush()
        return relation

    async def list_patients(self, user_id: str | int) -> list[tuple[ConsumerPatientRelation, Patient]]:
        rows = await self.session.execute(
            select(ConsumerPatientRelation, Patient)
            .join(Patient, Patient.id == ConsumerPatientRelation.patient_id)
            .where(
                ConsumerPatientRelation.consumer_user_id == _id(user_id, "consumer_user"),
                ConsumerPatientRelation.status == "ACTIVE",
            )
            .order_by(ConsumerPatientRelation.created_at)
        )
        return list(rows.tuples().all())


class ConsultationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self, *, user_id: str | int, patient_id: str | int, consultation_type: str
    ) -> Consultation:
        consultation_id = generate_snowflake_id()
        consultation = Consultation(
            id=consultation_id,
            consumer_user_id=_id(user_id, "consumer_user"),
            patient_id=_id(patient_id, "patient"),
            thread_id=str(consultation_id),
            consultation_type=consultation_type,
            status="CREATED",
            source_channel="wechat_mini_program",
        )
        self.session.add(consultation)
        await self.session.commit()
        await self.session.refresh(consultation)
        return consultation

    async def get(self, consultation_id: str | int) -> Consultation | None:
        return await self.session.scalar(
            select(Consultation).where(Consultation.id == _id(consultation_id, "consultation"))
        )

    async def can_access(self, consultation_id: str | int, user_id: str | int) -> bool:
        return await self.access_permission(consultation_id, user_id) is not None

    async def access_permission(
        self, consultation_id: str | int, user_id: str | int
    ) -> str | None:
        consultation = await self.get(consultation_id)
        if consultation is None:
            return None
        database_user_id = _id(user_id, "consumer_user")
        if consultation.consumer_user_id == database_user_id:
            return "MANAGE"
        grant = await self.session.scalar(
            select(ConsultationAccessGrant)
            .join(
                ConsultationShareGrant,
                ConsultationShareGrant.id == ConsultationAccessGrant.share_grant_id,
            )
            .where(
                ConsultationAccessGrant.consultation_id == consultation.id,
                ConsultationAccessGrant.consumer_user_id == database_user_id,
                ConsultationAccessGrant.status == "ACTIVE",
                ConsultationShareGrant.status == "ACTIVE",
            )
        )
        return grant.permission if grant is not None else None

    async def list_for_user(self, user_id: str | int) -> list[Consultation]:
        database_user_id = _id(user_id, "consumer_user")
        shared_ids = select(ConsultationAccessGrant.consultation_id).where(
            ConsultationAccessGrant.consumer_user_id == database_user_id,
            ConsultationAccessGrant.status == "ACTIVE",
        )
        return list(
            (
                await self.session.scalars(
                    select(Consultation)
                    .where(
                        or_(
                            Consultation.consumer_user_id == database_user_id,
                            Consultation.id.in_(shared_ids),
                        )
                    )
                    .order_by(Consultation.updated_at.desc())
                )
            ).all()
        )

    async def add_message(
        self,
        *,
        consultation_id: str | int,
        client_message_id: str,
        sender_type: str,
        sender_id: str | int | None,
        content: str,
        content_type: str = "text",
        metadata: dict[str, Any] | None = None,
    ) -> tuple[ConsultationMessage, bool]:
        database_consultation_id = _id(consultation_id, "consultation")
        existing = await self.session.scalar(
            select(ConsultationMessage).where(
                ConsultationMessage.consultation_id == database_consultation_id,
                ConsultationMessage.client_message_id == client_message_id,
            )
        )
        if existing is not None:
            return existing, False
        message = ConsultationMessage(
            consultation_id=database_consultation_id,
            client_message_id=client_message_id,
            sender_type=sender_type,
            sender_id=_id(sender_id, "consumer_user") if sender_id is not None else None,
            content_type=content_type,
            content=content,
            metadata_json=metadata,
        )
        self.session.add(message)
        try:
            await self.session.commit()
            await self.session.refresh(message)
            return message, True
        except IntegrityError:
            await self.session.rollback()
            duplicate = await self.session.scalar(
                select(ConsultationMessage).where(
                    ConsultationMessage.consultation_id == database_consultation_id,
                    ConsultationMessage.client_message_id == client_message_id,
                )
            )
            if duplicate is None:
                raise
            return duplicate, False

    async def messages(self, consultation_id: str | int) -> list[ConsultationMessage]:
        return list(
            (
                await self.session.scalars(
                    select(ConsultationMessage)
                    .where(ConsultationMessage.consultation_id == _id(consultation_id, "consultation"))
                    .order_by(ConsultationMessage.created_at, ConsultationMessage.id)
                )
            ).all()
        )

    async def set_status(
        self,
        consultation_id: str | int,
        status: str,
        *,
        risk_level: str | None = None,
        department_code: str | None = None,
        failure_stage: str | None = None,
        error_code: str | None = None,
    ) -> None:
        consultation = await self.get(consultation_id)
        if consultation is None:
            raise LookupError("CONSULTATION_NOT_FOUND")
        consultation.status = status
        if risk_level is not None:
            consultation.risk_level = risk_level
        if department_code is not None:
            consultation.recommended_department_code = department_code
        consultation.failure_stage = failure_stage
        consultation.error_code = error_code
        await self.session.commit()

    async def link_case(self, consultation_id: str | int, case_id: str | int, *, commit: bool = True) -> None:
        consultation = await self.get(consultation_id)
        if consultation is None:
            raise LookupError("CONSULTATION_NOT_FOUND")
        consultation.linked_case_id = _id(case_id, "case")
        consultation.status = "ESCALATED"
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()


class ShareGrantRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        consultation_id: str | int,
        created_by: str | int,
        token_hash: str,
        permission: str,
        expires_at: datetime,
        max_uses: int,
    ) -> ConsultationShareGrant:
        grant = ConsultationShareGrant(
            consultation_id=_id(consultation_id, "consultation"),
            created_by=_id(created_by, "consumer_user"),
            share_token_hash=token_hash,
            permission=permission,
            expires_at=expires_at,
            max_uses=max_uses,
            status="ACTIVE",
        )
        self.session.add(grant)
        await self.session.commit()
        await self.session.refresh(grant)
        return grant

    async def redeem(self, token_hash: str, user_id: str | int) -> ConsultationShareGrant:
        grant = await self.session.scalar(
            select(ConsultationShareGrant)
            .where(ConsultationShareGrant.share_token_hash == token_hash)
            .with_for_update()
        )
        if grant is None or grant.status != "ACTIVE":
            raise LookupError("SHARE_TOKEN_INVALID")
        expires_at = grant.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC):
            grant.status = "EXPIRED"
            await self.session.commit()
            raise LookupError("SHARE_TOKEN_EXPIRED")
        if grant.used_count >= grant.max_uses:
            raise LookupError("SHARE_TOKEN_MAX_USES")
        database_user_id = _id(user_id, "consumer_user")
        access = await self.session.scalar(
            select(ConsultationAccessGrant).where(
                ConsultationAccessGrant.consultation_id == grant.consultation_id,
                ConsultationAccessGrant.consumer_user_id == database_user_id,
            )
        )
        if access is None:
            self.session.add(
                ConsultationAccessGrant(
                    consultation_id=grant.consultation_id,
                    consumer_user_id=database_user_id,
                    share_grant_id=grant.id,
                    permission=grant.permission,
                    status="ACTIVE",
                )
            )
            grant.used_count += 1
        elif access.status != "ACTIVE":
            access.status = "ACTIVE"
            access.share_grant_id = grant.id
            grant.used_count += 1
        await self.session.commit()
        return grant

    async def revoke(self, grant_id: str | int, user_id: str | int) -> bool:
        grant = await self.session.get(ConsultationShareGrant, _id(grant_id, "share_grant"))
        if grant is None or grant.created_by != _id(user_id, "consumer_user"):
            return False
        grant.status = "REVOKED"
        accesses = (
            await self.session.scalars(
                select(ConsultationAccessGrant).where(
                    ConsultationAccessGrant.share_grant_id == grant.id
                )
            )
        ).all()
        for access in accesses:
            access.status = "REVOKED"
        await self.session.commit()
        return True


class ConsentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(self, user_id: str | int, agreement_type: str, version: str) -> ConsumerConsentRecord:
        record = ConsumerConsentRecord(
            consumer_user_id=_id(user_id, "consumer_user"),
            agreement_type=agreement_type,
            agreement_version=version,
            consented_at=datetime.now(UTC),
        )
        self.session.add(record)
        await self.session.commit()
        return record
