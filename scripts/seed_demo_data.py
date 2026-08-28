import asyncio
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.persistence.database import close_database, get_session_factory, initialize_schema
from app.core.config import get_settings
from app.core.passwords import hash_password
from app.persistence.models import (
    Allergy,
    Doctor,
    ImagingReport,
    LabResult,
    MedicalVisit,
    Medication,
    Patient,
)


async def seed() -> None:
    """初始化隔离环境演示数据，重复执行时不覆盖已有业务数据。"""
    await initialize_schema()
    async with get_session_factory()() as session:
        existing = await session.scalar(select(Patient.id).limit(1))
        if existing:
            print("样例数据已经存在，本次未做修改")
            return

        now = datetime.now(UTC)
        # 先准备基础档案，再批量创建与患者业务编号关联的临床记录。
        patients = [
            Patient(
                id="PT-CARDIO",
                display_name="心内科患者 A",
                birth_date=date(1968, 5, 10),
                sex="male",
                summary_json={"sandbox": True, "history": ["高血压病史 8 年"], "privacy": "隔离环境样例数据"},
                data_scope="sandbox",
                source_channel="seed",
            ),
            Patient(
                id="PT-GASTRO",
                display_name="消化科患者 B",
                birth_date=date(1986, 11, 2),
                sex="female",
                summary_json={"sandbox": True, "history": ["间断胃部不适"], "privacy": "隔离环境样例数据"},
                data_scope="sandbox",
                source_channel="seed",
            ),
            Patient(
                id="PT-LOW",
                display_name="低风险患者 C",
                birth_date=date(1994, 3, 20),
                sex="other",
                summary_json={"sandbox": True, "history": [], "privacy": "隔离环境样例数据"},
                data_scope="sandbox",
                source_channel="seed",
            ),
        ]
        doctors = [
            Doctor(id="DEMO-D-001", account=get_settings().login_account, password_hash=hash_password(get_settings().login_password), name="李医生", department="心内科", title="主治医师"),
            Doctor(id="DEMO-D-002", account="doctor2", password_hash=hash_password(get_settings().login_password), name="王医生", department="消化内科", title="副主任医师"),
        ]
        session.add_all(patients + doctors)
        await session.flush()
        session.add_all(
            [
                MedicalVisit(
                    patient_id="PT-CARDIO",
                    visit_time=now - timedelta(days=1),
                    department="心内科",
                    chief_complaint="活动后胸痛 2 天",
                    record_json={"blood_pressure": "168/102 mmHg", "pulse": "96 bpm", "sandbox": True},
                ),
                LabResult(
                    patient_id="PT-CARDIO",
                    observed_at=now - timedelta(hours=20),
                    test_name="高敏肌钙蛋白 I",
                    value="0.018 ng/mL",
                    reference_range="<0.026 ng/mL",
                    abnormal_flag="normal",
                ),
                ImagingReport(
                    patient_id="PT-CARDIO",
                    observed_at=now - timedelta(hours=18),
                    modality="ECG",
                    body_part="心脏",
                    findings="窦性心律，部分导联 ST-T 非特异性改变",
                    impression="建议结合症状及动态心电图复查",
                ),
                Medication(
                    patient_id="PT-CARDIO",
                    name="氨氯地平",
                    dose="5 mg qd",
                    route="口服",
                    started_at=now - timedelta(days=180),
                ),
                Allergy(
                    patient_id="PT-CARDIO",
                    substance="青霉素",
                    reaction="皮疹",
                    severity="mild",
                    observed_at=now - timedelta(days=1000),
                ),
                MedicalVisit(
                    patient_id="PT-GASTRO",
                    visit_time=now - timedelta(days=2),
                    department="消化内科",
                    chief_complaint="上腹痛伴恶心 3 天，呕吐 1 次",
                    record_json={"temperature": "37.2 C", "abdomen": "上腹轻压痛", "sandbox": True},
                ),
                LabResult(
                    patient_id="PT-GASTRO",
                    observed_at=now - timedelta(days=2),
                    test_name="血常规白细胞",
                    value="9.2 x10^9/L",
                    reference_range="3.5-9.5 x10^9/L",
                    abnormal_flag="normal",
                ),
                MedicalVisit(
                    patient_id="PT-LOW",
                    visit_time=now - timedelta(days=7),
                    department="全科",
                    chief_complaint="轻微鼻塞 1 天，无发热",
                    record_json={"temperature": "36.6 C", "sandbox": True},
                ),
            ]
        )
        await session.commit()
        print("已写入 3 名隔离环境患者和 2 名医生样例数据")


async def main() -> None:
    """运行演示数据初始化，并在结束时释放数据库连接。"""
    try:
        await seed()
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
