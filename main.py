import uuid
import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json

from database import engine, Base, get_db
from models import RCAInvestigation
from schemas import ChatTurnRequest, RCAFormState, SaveRCARequest
from agent import rca_langgraph_app

# Create PostgreSQL tables automatically on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AIVOA.AI Root Cause Analysis (RCA) Co-pilot API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "module": "AIVOA_API_RCA_COPILOT"}


@app.post("/api/copilot/chat")
def copilot_chat(payload: ChatTurnRequest):
    """Handles both initial text/email intake (log_rca_investigation) and follow-up edits (edit_rca_investigation)."""
    try:
        initial_state = {
            "input_type": "text_chat",
            "user_input": payload.user_message,
            "document_filename": "",
            "current_form": payload.current_form.model_dump(),
            "updated_form": {},
            "tool_used": "",
            "assistant_message": "",
            "modified_sections": [],
        }
        result = rca_langgraph_app.invoke(initial_state)
        return {
            "tool_used": result["tool_used"],
            "assistant_message": result["assistant_message"],
            "updated_form": result["updated_form"],
            "modified_sections": result["modified_sections"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Co-pilot error: {str(e)}")


@app.post("/api/copilot/upload")
async def copilot_upload_document(
    file: UploadFile = File(...),
    current_form_json: str = Form(default="{}"),
):
    """Accepts a PDF or text/email file, extracts text, and triggers extract_investigation_document."""
    try:
        file_bytes = await file.read()
        filename = file.filename or "uploaded_document.pdf"
        extracted_text = ""

        if filename.lower().endswith(".pdf"):
            pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in pdf_doc:
                extracted_text += page.get_text("text") + "\n"
            pdf_doc.close()
        else:
            extracted_text = file_bytes.decode("utf-8", errors="ignore")

        if not extracted_text.strip():
            raise HTTPException(
                status_code=400, detail="Could not extract readable text from uploaded file."
            )

        try:
            current_form_dict = json.loads(current_form_json)
            validated_current = RCAFormState(**current_form_dict).model_dump()
        except Exception:
            validated_current = RCAFormState().model_dump()

        initial_state = {
            "input_type": "document_upload",
            "user_input": extracted_text,
            "document_filename": filename,
            "current_form": validated_current,
            "updated_form": {},
            "tool_used": "",
            "assistant_message": "",
            "modified_sections": [],
        }
        result = rca_langgraph_app.invoke(initial_state)
        return {
            "tool_used": result["tool_used"],
            "filename": filename,
            "extracted_preview": extracted_text[:400] + "...",
            "assistant_message": result["assistant_message"],
            "updated_form": result["updated_form"],
            "modified_sections": result["modified_sections"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document extraction error: {str(e)}")


@app.post("/api/rca/save")
def save_investigation(payload: SaveRCARequest, db: Session = Depends(get_db)):
    """Persists the reviewed RCA investigation to PostgreSQL."""
    data = payload.form_data
    if not data.api_product_name:
        raise HTTPException(
            status_code=400,
            detail="Cannot save an empty RCA form. Populate via the AI Co-pilot first.",
        )

    rca_num = f"RCA-API-{uuid.uuid4().hex[:6].upper()}"
    status_label = (
        "Closed - QP Verified" if data.qp_verified else "Under Investigation (AI Draft Reviewed)"
    )

    record = RCAInvestigation(
        rca_number=rca_num,
        deviation_ref_id=data.deviation_ref_id or "DEV-UNASSIGNED",
        api_product_name=data.api_product_name,
        manufacturing_stage=data.manufacturing_stage,
        batch_number=data.batch_number,
        equipment_id=data.equipment_id,
        site_block=data.site_block,
        incident_date=data.incident_date,
        severity=data.severity,
        risk_priority_number=data.risk_priority_number,
        problem_summary=data.problem_summary,
        cqa_cpp_impacted=data.cqa_cpp_impacted,
        immediate_containment=data.immediate_containment,
        fishbone_factors=[f.model_dump() for f in data.fishbone_factors],
        five_whys=[w.model_dump() for w in data.five_whys],
        suspected_root_cause=data.suspected_root_cause,
        contributing_factors=data.contributing_factors,
        missing_evidence=data.missing_evidence,
        capa_recommendations=[c.model_dump() for c in data.capa_recommendations],
        effectiveness_check_plan=data.effectiveness_check_plan,
        qp_verified=data.qp_verified,
        qp_reviewer_name=data.qp_reviewer_name,
        qp_verification_notes=data.qp_verification_notes,
        investigation_status=status_label,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "message": "RCA Investigation saved to PostgreSQL successfully.",
        "id": record.id,
        "rca_number": record.rca_number,
        "status": record.investigation_status,
        "created_at": record.created_at,
    }


@app.get("/api/rca/list")
def list_investigations(db: Session = Depends(get_db)):
    records = (
        db.query(RCAInvestigation)
        .order_by(RCAInvestigation.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "rca_number": r.rca_number,
            "deviation_ref_id": r.deviation_ref_id,
            "api_product_name": r.api_product_name,
            "batch_number": r.batch_number,
            "severity": r.severity,
            "qp_verified": r.qp_verified,
            "status": r.investigation_status,
            "created_at": r.created_at,
        }
        for r in records
    ]


@app.get("/api/rca/{rca_id}")
def get_investigation(rca_id: int, db: Session = Depends(get_db)):
    r = db.query(RCAInvestigation).filter(RCAInvestigation.id == rca_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return {
        "rca_number": r.rca_number,
        "form_data": {
            "deviation_ref_id": r.deviation_ref_id,
            "api_product_name": r.api_product_name,
            "manufacturing_stage": r.manufacturing_stage,
            "batch_number": r.batch_number,
            "equipment_id": r.equipment_id,
            "site_block": r.site_block,
            "incident_date": r.incident_date,
            "severity": r.severity,
            "risk_priority_number": r.risk_priority_number,
            "problem_summary": r.problem_summary,
            "cqa_cpp_impacted": r.cqa_cpp_impacted,
            "immediate_containment": r.immediate_containment,
            "fishbone_factors": r.fishbone_factors,
            "five_whys": r.five_whys,
            "suspected_root_cause": r.suspected_root_cause,
            "contributing_factors": r.contributing_factors,
            "missing_evidence": r.missing_evidence,
            "capa_recommendations": r.capa_recommendations,
            "effectiveness_check_plan": r.effectiveness_check_plan,
            "qp_verified": r.qp_verified,
            "qp_reviewer_name": r.qp_reviewer_name,
            "qp_verification_notes": r.qp_verification_notes,
        },
    }