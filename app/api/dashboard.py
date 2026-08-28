from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import case as sql_case
from sqlalchemy import func, select

from app.api.auth import get_current_doctor
from app.persistence.database import get_session_factory
from app.persistence.models import MedicalCase
from app.persistence.repositories import CaseRepository

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_doctor)])


@router.get("/summary")
async def dashboard_summary() -> dict:
    now = datetime.now(UTC)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = today - timedelta(days=6)
    async with get_session_factory()() as session:
        row = (
            await session.execute(
                select(
                    func.sum(sql_case((MedicalCase.created_at >= today, 1), else_=0)),
                    func.sum(sql_case((MedicalCase.status == "WAITING_REVIEW", 1), else_=0)),
                    func.sum(sql_case((MedicalCase.risk_level.in_(["high", "emergency"]), 1), else_=0)),
                    func.sum(sql_case((MedicalCase.status == "FINAL", 1), else_=0)),
                )
            )
        ).one()
        trends = (
            await session.execute(
                select(func.date(MedicalCase.created_at), func.count())
                .where(MedicalCase.created_at >= start)
                .group_by(func.date(MedicalCase.created_at))
                .order_by(func.date(MedicalCase.created_at))
            )
        ).all()
        pending = await CaseRepository(session).list(page=1, page_size=5, pending_only=True)
    return {
        "today_cases": int(row[0] or 0),
        "pending_reviews": int(row[1] or 0),
        "high_risk_cases": int(row[2] or 0),
        "completed_cases": int(row[3] or 0),
        "trend": [{"date": str(item[0]), "count": item[1]} for item in trends],
        "pending_items": pending["items"],
    }

