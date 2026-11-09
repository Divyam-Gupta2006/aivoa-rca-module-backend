from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from database import Base


class RCAInvestigation(Base):
    __tablename__ = "rca_investigations"

    id = Column(Integer, primary_key=True, index=True)
    rca_number = Column(String(50), unique=True, index=True, nullable=False)
    deviation_ref_id = Column(String(100), nullable=False)
    api_product_name = Column(String(200), nullable=False)
    manufacturing_stage = Column(String(200))
    batch_number = Column(String(100), index=True)
    equipment_id = Column(String(100))
    site_block = Column(String(100))
    incident_date = Column(String(50))
    severity = Column(String(50))
    risk_priority_number = Column(String(50))

    # Problem & Containment
    problem_summary = Column(Text)
    cqa_cpp_impacted = Column(Text)
    immediate_containment = Column(JSON, default=list)

    # Structured RCA Methodologies
    fishbone_factors = Column(JSON, default=list)
    five_whys = Column(JSON, default=list)

    # Conclusions & Evidence Gaps
    suspected_root_cause = Column(Text)
    contributing_factors = Column(JSON, default=list)
    missing_evidence = Column(JSON, default=list)

    # CAPA & Effectiveness
    capa_recommendations = Column(JSON, default=list)
    effectiveness_check_plan = Column(Text)

    # Human-in-the-Loop QA / QP Verification
    qp_verified = Column(Boolean, default=False)
    qp_reviewer_name = Column(String(150), default="")
    qp_verification_notes = Column(Text, default="")
    investigation_status = Column(String(50), default="Draft - AI Populated")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )