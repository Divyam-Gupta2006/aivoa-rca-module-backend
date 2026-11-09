import os
import json
from typing import TypedDict, List, Literal
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from schemas import RCAFormState, RCAInvestigationExtraction, LLMExtractionResult

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_CHAT_MODEL") or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def get_structured_llm():
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        temperature=0.1,
    )
    return llm.with_structured_output(RCAInvestigationExtraction)


class AgentGraphState(TypedDict):
    input_type: Literal["text_chat", "document_upload"]
    user_input: str
    document_filename: str
    current_form: dict
    updated_form: dict
    tool_used: str
    assistant_message: str
    modified_sections: List[str]


SYSTEM_GMP_PROMPT = """You are the AIVOA.AI Pharmaceutical Root Cause Analysis (RCA) Co-pilot for an Active Pharmaceutical Ingredient (API) manufacturer operating under ICH Q7, ICH Q9, ICH Q10, and 21 CFR Part 211.

CRITICAL GMP & PRODUCT RULES:
1. Extract and populate all available API deviation metadata (Product Name, Stage, Batch Number, Equipment ID, Site/Block, Date, Severity, ICH Q9 RPN Risk Score, Problem Summary, CQA/CPP impacted, Immediate Containment).
2. Perform a thorough 6M Fishbone Analysis across ALL 6 categories: Man, Machine, Method, Material, Measurement, Environment.
3. Build a rigorous 5 Whys causal chain (Steps 1 to 5) tracing the physical/chemical excursion to the systemic root cause.
4. EVIDENCE RULE: All AI-generated causes MUST have status='AI Suggested (Unverified)' UNLESS the user or document explicitly provides objective verification evidence confirming the cause (in which case set status='Confirmed by Evidence') or explicitly rules a cause out (set status='Ruled Out').
5. Identify specific 'missing_evidence' (e.g., SCADA valve actuator logs, sensor calibration certificates, raw material CoA, preventive maintenance logs) required to close investigation gaps.
6. Recommend 3-tier CAPAs: Correction (Immediate), Corrective Action (CA), and Preventive Action (PA) with clear scientific rationale, owner department, and target days, plus a 30/60/90-day Effectiveness Check Plan.
7. Provide a helpful assistant_message summarizing what was extracted, key findings, and open evidence gaps.
"""


def compute_modified_sections(old_form: dict, new_form: dict) -> List[str]:
    """Computes which UI cards changed so the frontend can flash green diff highlights."""
    changed = []
    header_keys = [
        "deviation_ref_id", "api_product_name", "manufacturing_stage",
        "batch_number", "equipment_id", "site_block", "incident_date",
        "severity", "risk_priority_number"
    ]
    if any(old_form.get(k) != new_form.get(k) for k in header_keys):
        changed.append("header")

    problem_keys = ["problem_summary", "cqa_cpp_impacted", "immediate_containment"]
    if any(old_form.get(k) != new_form.get(k) for k in problem_keys):
        changed.append("problem_containment")

    if old_form.get("fishbone_factors") != new_form.get("fishbone_factors"):
        changed.append("fishbone")

    if old_form.get("five_whys") != new_form.get("five_whys"):
        changed.append("five_whys")

    rca_keys = ["suspected_root_cause", "contributing_factors", "missing_evidence"]
    if any(old_form.get(k) != new_form.get(k) for k in rca_keys):
        changed.append("root_cause_evidence")

    capa_keys = ["capa_recommendations", "effectiveness_check_plan"]
    if any(old_form.get(k) != new_form.get(k) for k in capa_keys):
        changed.append("capa")

    return changed


# ---------------------------------------------------------
# NODE 1: Router Node
# ---------------------------------------------------------
def router_node(state: AgentGraphState) -> Literal[
    "extract_investigation_document",
    "log_rca_investigation",
    "edit_rca_investigation",
]:
    if state["input_type"] == "document_upload":
        return "extract_investigation_document"

    current = state.get("current_form", {})
    # If the form already has a product name or problem summary, route to the Edit tool
    has_existing_data = bool(
        current.get("api_product_name", "").strip()
        or current.get("problem_summary", "").strip()
    )
    if has_existing_data:
        return "edit_rca_investigation"
    return "log_rca_investigation"


# ---------------------------------------------------------
# TOOL 1: Log RCA Investigation Tool (Initial Text/Email Intake)
# ---------------------------------------------------------
def log_rca_investigation_node(state: AgentGraphState) -> AgentGraphState:
    structured_llm = get_structured_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_GMP_PROMPT + "\nTool Mode: LOG_RCA_INVESTIGATION. Extract all details from the incident text/email and populate the complete RCA form from scratch. Summarize findings in assistant_message."),
        ("human", "Incident Report / Email Text:\n{user_input}")
    ])
    chain = prompt | structured_llm
    result: RCAInvestigationExtraction = chain.invoke({"user_input": state["user_input"]})

    res_dict = result.model_dump()
    assistant_msg = res_dict.pop("assistant_message", "").strip()
    if not assistant_msg:
        prod = res_dict.get("api_product_name") or "API Batch"
        batch = res_dict.get("batch_number") or ""
        assistant_msg = f"Incident logged for **{prod}** (Batch: {batch}). Extracted process parameters, 6M Ishikawa Fishbone, 5 Whys, and CAPA recommendations."

    new_form_dict = res_dict
    modified = compute_modified_sections(state["current_form"], new_form_dict)

    return {
        **state,
        "tool_used": "log_rca_investigation",
        "updated_form": new_form_dict,
        "assistant_message": assistant_msg,
        "modified_sections": modified,
    }


# ---------------------------------------------------------
# TOOL 2: Edit RCA Investigation Tool (Stateful NL Modification)
# ---------------------------------------------------------
def edit_rca_investigation_node(state: AgentGraphState) -> AgentGraphState:
    structured_llm = get_structured_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_GMP_PROMPT + """
Tool Mode: EDIT_RCA_INVESTIGATION.
CRITICAL INSTRUCTION:
- You are updating an EXISTING Root Cause Analysis form based on the user's natural language instruction or newly supplied investigation evidence.
- PRESERVE all existing fields in Current Form State that are not affected by the user's request.
- If the user corrects a parameter (e.g., batch number, equipment ID, impurity value, severity), update it and recalculate risk/impact if needed.
- If the user provides new evidence that rules out a cause or confirms a root cause, update the corresponding Fishbone factor status ('Ruled Out' or 'Confirmed by Evidence'), refine the 5 Whys and Suspected Root Cause, remove resolved items from 'missing_evidence', and update the CAPA recommendations accordingly.
- Summarize changes in assistant_message."""),
        ("human", "Current RCA Form State (JSON):\n{current_form}\n\nUser Update / New Investigation Evidence:\n{user_input}")
    ])
    chain = prompt | structured_llm
    result: RCAInvestigationExtraction = chain.invoke({
        "current_form": json.dumps(state["current_form"]),
        "user_input": state["user_input"],
    })

    res_dict = result.model_dump()
    assistant_msg = res_dict.pop("assistant_message", "").strip()
    if not assistant_msg:
        assistant_msg = "Updated the RCA investigation form based on your input."

    merged_form = dict(state["current_form"])
    for k, v in res_dict.items():
        if v or (isinstance(v, list) and len(v) > 0):
            merged_form[k] = v

    modified = compute_modified_sections(state["current_form"], merged_form)

    return {
        **state,
        "tool_used": "edit_rca_investigation",
        "updated_form": merged_form,
        "assistant_message": assistant_msg,
        "modified_sections": modified,
    }


# ---------------------------------------------------------
# TOOL 3: Document Extraction Tool (PDF / Investigation File Intake)
# ---------------------------------------------------------
def extract_investigation_document_node(state: AgentGraphState) -> AgentGraphState:
    structured_llm = get_structured_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_GMP_PROMPT + "\nTool Mode: EXTRACT_INVESTIGATION_DOCUMENT. Extract all parameters, lab data, process trends, and timeline events from the uploaded document to populate the complete RCA & CAPA form. Summarize key findings in assistant_message."),
        ("human", "Uploaded Document Filename: {filename}\n\nExtracted Document Text:\n{user_input}")
    ])
    chain = prompt | structured_llm
    result: RCAInvestigationExtraction = chain.invoke({
        "filename": state.get("document_filename", "incident_report.pdf"),
        "user_input": state["user_input"],
    })

    res_dict = result.model_dump()
    assistant_msg = res_dict.pop("assistant_message", "").strip()
    if not assistant_msg:
        filename = state.get("document_filename", "the uploaded document")
        prod = res_dict.get("api_product_name") or "API Deviation"
        batch = res_dict.get("batch_number") or ""
        assistant_msg = f"Successfully parsed and extracted investigation parameters from `{filename}` for **{prod}** (Batch: {batch}). 6M Fishbone, 5 Whys, open evidence gaps, and CAPA recommendations have been populated."

    new_form_dict = res_dict
    modified = compute_modified_sections(state["current_form"], new_form_dict)

    return {
        **state,
        "tool_used": "extract_investigation_document",
        "updated_form": new_form_dict,
        "assistant_message": assistant_msg,
        "modified_sections": modified,
    }


# ---------------------------------------------------------
# Compile LangGraph Workflow
# ---------------------------------------------------------
workflow = StateGraph(AgentGraphState)

workflow.add_node("log_rca_investigation", log_rca_investigation_node)
workflow.add_node("edit_rca_investigation", edit_rca_investigation_node)
workflow.add_node("extract_investigation_document", extract_investigation_document_node)

workflow.set_conditional_entry_point(
    router_node,
    {
        "log_rca_investigation": "log_rca_investigation",
        "edit_rca_investigation": "edit_rca_investigation",
        "extract_investigation_document": "extract_investigation_document",
    },
)

workflow.add_edge("log_rca_investigation", END)
workflow.add_edge("edit_rca_investigation", END)
workflow.add_edge("extract_investigation_document", END)

rca_langgraph_app = workflow.compile()
