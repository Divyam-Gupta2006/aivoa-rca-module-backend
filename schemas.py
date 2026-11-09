from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class FishboneFactor(BaseModel):
    category: Literal[
        "Man", "Machine", "Method", "Material", "Measurement", "Environment"
    ] = Field(description="6M Ishikawa category")
    cause: str = Field(description="Specific technical potential cause in API manufacturing")
    likelihood: Literal["High", "Medium", "Low"] = Field(
        description="Assessed probability based on available evidence"
    )
    status: Literal[
        "AI Suggested (Unverified)", "Ruled Out", "Confirmed by Evidence"
    ] = Field(
        default="AI Suggested (Unverified)",
        description="Must remain 'AI Suggested (Unverified)' unless objective evidence is explicitly provided",
    )
    evidence_note: str = Field(
        description="Supporting evidence cited OR specific evidence required to verify this cause"
    )


class WhyStep(BaseModel):
    step_number: int = Field(description="Step 1 through 5")
    question: str = Field(description="The 'Why' question asked")
    answer: str = Field(description="Technical answer based on process/engineering evidence")


class CAPAItem(BaseModel):
    capa_type: Literal[
        "Correction (Immediate)", "Corrective Action (CA)", "Preventive Action (PA)"
    ]
    action_description: str = Field(description="Specific GMP action to take")
    scientific_rationale: str = Field(
        description="Short explanation of how this addresses the root cause or prevents recurrence"
    )
    owner_department: str = Field(
        description="e.g., Process Engineering, QC Lab, Maintenance, Production, QA"
    )
    target_completion_days: int = Field(description="Recommended timeline in days (e.g., 7, 30, 60)")


class RCAFormState(BaseModel):
    deviation_ref_id: str = Field(default="", description="Deviation ID e.g. DEV-API-2026-014")
    api_product_name: str = Field(default="", description="Name of Active Pharmaceutical Ingredient")
    manufacturing_stage: str = Field(default="", description="e.g. Stage-III Crystallization / Vacuum Drying")
    batch_number: str = Field(default="", description="Batch or Lot number")
    equipment_id: str = Field(default="", description="Reactor, Dryer, Centrifuge, or HPLC ID")
    site_block: str = Field(default="", description="Manufacturing Plant Block / Suite")
    incident_date: str = Field(default="", description="Date/Time of incident")
    severity: Literal["Critical", "Major", "Minor", ""] = Field(default="")
    risk_priority_number: str = Field(
        default="", description="ICH Q9 Risk Score e.g., RPN 48 (High) - Sev:4 x Occ:3 x Det:4"
    )

    problem_summary: str = Field(
        default="", description="Detailed 5W1H technical summary of the API quality deviation"
    )
    cqa_cpp_impacted: str = Field(
        default="",
        description="Critical Process Parameters (CPP) and Critical Quality Attributes (CQA) impacted with spec limits",
    )
    immediate_containment: List[str] = Field(
        default_factory=list,
        description="Immediate batch quarantine, hold tags, or containment steps taken",
    )

    fishbone_factors: List[FishboneFactor] = Field(
        default_factory=list,
        description="6M Fishbone analysis covering Man, Machine, Method, Material, Measurement, Environment",
    )
    five_whys: List[WhyStep] = Field(
        default_factory=list,
        description="5 Whys causal chain drilling down into the primary suspected cause",
    )

    suspected_root_cause: str = Field(
        default="",
        description="Primary root cause statement (treated as hypothesis until verified by evidence & QP)",
    )
    contributing_factors: List[str] = Field(
        default_factory=list,
        description="Secondary contributing factors that exacerbated the deviation",
    )
    missing_evidence: List[str] = Field(
        default_factory=list,
        description="Missing logs, calibration records, or test data needed to conclusively verify the root cause",
    )

    capa_recommendations: List[CAPAItem] = Field(
        default_factory=list,
        description="Corrections, Corrective Actions, and Preventive Actions with explanations",
    )
    effectiveness_check_plan: str = Field(
        default="",
        description="Plan to verify CAPA effectiveness over future API batches (30/60/90 days)",
    )

    qp_verified: bool = Field(default=False)
    qp_reviewer_name: str = Field(default="")
    qp_verification_notes: str = Field(default="")


class RCAInvestigationExtraction(RCAFormState):
    assistant_message: str = Field(
        default="",
        description="Conversational QA response summarizing what was extracted or updated in GMP terms, highlighting key findings and open evidence gaps.",
    )


class LLMExtractionResult(BaseModel):
    assistant_message: str = Field(
        description="Conversational response explaining what was extracted/updated, key findings, and asking about missing evidence."
    )
    updated_form: RCAFormState


class ChatTurnRequest(BaseModel):
    user_message: str
    current_form: RCAFormState


class SaveRCARequest(BaseModel):
    form_data: RCAFormState