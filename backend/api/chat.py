import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.decision_service import run_decision_pipeline


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)


# =========================================================
# REQUEST MODEL
# =========================================================

class ChatRequest(BaseModel):

    message: str

    carbon_budget: float = 100

    simulate_grid_failure: bool = False


# =========================================================
# WORKLOAD TYPE DETECTION
# =========================================================

def detect_workload_type(message: str):

    text = message.lower()

    if any(word in text for word in [
        "training",
        "train model",
        "train an ai",
        "train a model",
        "machine learning training"
    ]):
        return "training"

    if any(word in text for word in [
        "inference",
        "prediction",
        "predict",
        "classification",
        "generate prediction"
    ]):
        return "inference"

    return "batch"


# =========================================================
# PRIORITY DETECTION
# =========================================================

def detect_priority(message: str):

    text = message.lower()

    urgent_words = [
        "urgent",
        "urgently",
        "emergency",
        "critical",
        "immediately",
        "immediate",
        "asap",
        "as soon as possible",
        "right now",
        "high priority"
    ]

    if any(word in text for word in urgent_words):
        return "urgent"

    low_priority_words = [
        "overnight",
        "whenever",
        "not urgent",
        "low priority",
        "can wait",
        "flexible",
        "later"
    ]

    if any(word in text for word in low_priority_words):
        return "low"

    return "normal"


# =========================================================
# WORKLOAD SIZE DETECTION
# =========================================================

def detect_workload_size(message: str):

    text = message.lower()

    # -----------------------------------------------------
    # Page-based workloads
    # -----------------------------------------------------

    page_match = re.search(
        r"(\d[\d,]*)\s*(?:pages?|page)",
        text
    )

    if page_match:

        pages = int(
            page_match.group(1).replace(",", "")
        )

        if pages >= 10000:
            return 1000

        if pages >= 5000:
            return 800

        if pages >= 1000:
            return 500

        if pages >= 500:
            return 300

        return 150

    # -----------------------------------------------------
    # Employee / record workloads
    # -----------------------------------------------------

    employee_match = re.search(
        r"(\d[\d,]*)\s*(?:employees?|workers?|users?)",
        text
    )

    if employee_match:

        employees = int(
            employee_match.group(1).replace(",", "")
        )

        if employees >= 10000:
            return 1000

        if employees >= 5000:
            return 800

        if employees >= 1000:
            return 500

        return 200

    # -----------------------------------------------------
    # Dataset size
    # -----------------------------------------------------

    dataset_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(gb|tb|million|billion)",
        text
    )

    if dataset_match:

        value = float(dataset_match.group(1))

        unit = dataset_match.group(2)

        if unit == "tb":
            return 1000

        if unit == "gb":
            return max(100, value)

        if unit == "million":
            return 500

        if unit == "billion":
            return 1000

    # -----------------------------------------------------
    # Keywords indicating a large workload
    # -----------------------------------------------------

    large_words = [
        "large dataset",
        "huge dataset",
        "massive dataset",
        "big dataset",
        "large report",
        "huge report",
        "massive report",
        "yearly report",
        "annual report",
        "consolidated",
        "bulk processing",
        "large batch",
        "big data"
    ]

    if any(word in text for word in large_words):
        return 500

    # -----------------------------------------------------
    # Default workload
    # -----------------------------------------------------

    return 100


# =========================================================
# RUNTIME DETECTION
# =========================================================

def detect_runtime(message: str, workload_size: float):

    text = message.lower()

    runtime_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)",
        text
    )

    if runtime_match:

        return float(
            runtime_match.group(1)
        )

    # -----------------------------------------------------
    # Intelligent prototype defaults
    # -----------------------------------------------------

    if workload_size >= 800:
        return 8

    if workload_size >= 500:
        return 5

    if workload_size >= 300:
        return 4

    if workload_size >= 150:
        return 3

    return 2


# =========================================================
# DEADLINE DETECTION
# =========================================================

def detect_deadline(message: str, priority: str):

    text = message.lower()

    deadline_match = re.search(
        r"deadline\s*(?:of|is|:)?\s*"
        r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)",
        text
    )

    if deadline_match:

        return float(
            deadline_match.group(1)
        )

    # -----------------------------------------------------
    # Urgent workloads
    # -----------------------------------------------------

    if priority == "urgent":

        return 2

    # -----------------------------------------------------
    # Explicit time phrases
    # -----------------------------------------------------

    if "within 1 hour" in text:
        return 1

    if "within 2 hours" in text:
        return 2

    if "within 4 hours" in text:
        return 4

    if "within 6 hours" in text:
        return 6

    if "within 12 hours" in text:
        return 12

    if "today" in text:
        return 12

    if "tonight" in text:
        return 12

    if "tomorrow" in text:
        return 24

    if "this week" in text:
        return 168

    # -----------------------------------------------------
    # Flexible workloads
    # -----------------------------------------------------

    if priority == "low":
        return 48

    # -----------------------------------------------------
    # Normal default
    # -----------------------------------------------------

    return 24


# =========================================================
# LOCATION DETECTION
# =========================================================

def detect_location(message: str):

    text = message.lower()

    locations = {

        "india": "IN",

        "germany": "DE",
        "france": "FR",
        "belgium": "BE",
        "netherlands": "NL",
        "denmark": "DK",

        "de": "DE",
        "fr": "FR",
        "be": "BE",
        "nl": "NL",
        "dk": "DK"
    }

    for name, code in locations.items():

        if re.search(
            r"\b" + re.escape(name) + r"\b",
            text
        ):
            return code

    return None


# =========================================================
# SPECIAL SCENARIO DETECTION
# =========================================================

def detect_scenario(message: str):

    text = message.lower()

    if any(word in text for word in [
        "emergency",
        "urgent",
        "critical",
        "asap",
        "immediately",
        "right now"
    ]):

        return "URGENT"

    if any(word in text for word in [
        "bank statement",
        "employee statement",
        "salary statement",
        "payroll",
        "financial report",
        "annual report",
        "yearly report"
    ]):

        return "FINANCIAL_BATCH"

    if any(word in text for word in [
        "5000 page",
        "5000 pages",
        "large report",
        "huge report",
        "massive report",
        "document summarization",
        "summarize a large"
    ]):

        return "LARGE_DOCUMENT"

    if any(word in text for word in [
        "train",
        "training",
        "train model"
    ]):

        return "MODEL_TRAINING"

    if any(word in text for word in [
        "inference",
        "prediction",
        "predict"
    ]):

        return "INFERENCE"

    if any(word in text for word in [
        "dataset",
        "data processing",
        "data analysis",
        "batch processing",
        "bulk processing"
    ]):

        return "DATA_PROCESSING"

    return "GENERAL"


# =========================================================
# BUILD WORKLOAD
# =========================================================

def build_workload(message: str, carbon_budget: float):

    workload_type = detect_workload_type(message)

    priority = detect_priority(message)

    workload_size = detect_workload_size(message)

    runtime_hours = detect_runtime(
        message,
        workload_size
    )

    deadline_hours = detect_deadline(
        message,
        priority
    )

    location = detect_location(message)

    scenario = detect_scenario(message)

    # -----------------------------------------------------
    # Scenario-specific adjustments
    # -----------------------------------------------------

    if scenario == "URGENT":

        priority = "urgent"

        deadline_hours = min(
            deadline_hours,
            2
        )

        # urgent work should not be given an
        # artificially long runtime

        runtime_hours = min(
            runtime_hours,
            2
        )


    elif scenario == "LARGE_DOCUMENT":

        workload_size = max(
            workload_size,
            500
        )

        runtime_hours = max(
            runtime_hours,
            5
        )

        deadline_hours = max(
            deadline_hours,
            24
        )


    elif scenario == "FINANCIAL_BATCH":

        workload_size = max(
            workload_size,
            500
        )

        runtime_hours = max(
            runtime_hours,
            4
        )

        deadline_hours = max(
            deadline_hours,
            24
        )


    elif scenario == "MODEL_TRAINING":

        workload_type = "training"

        workload_size = max(
            workload_size,
            500
        )

        runtime_hours = max(
            runtime_hours,
            6
        )

        deadline_hours = max(
            deadline_hours,
            24
        )


    elif scenario == "INFERENCE":

        workload_type = "inference"

        workload_size = min(
            workload_size,
            200
        )

        runtime_hours = min(
            runtime_hours,
            2
        )


    elif scenario == "DATA_PROCESSING":

        workload_type = "batch"

        workload_size = max(
            workload_size,
            200
        )


    return {

        "workload_type": workload_type,

        "runtime_hours": runtime_hours,

        "deadline_hours": deadline_hours,

        "latency_tolerance": (
            30
            if priority == "urgent"
            else 150
        ),

        "carbon_budget": carbon_budget,

        "priority": priority,

        "workload_size": workload_size,

        # Used by the decision layer if supported
        "preferred_region": location,

        "scenario": scenario
    }


# =========================================================
# CHAT ENDPOINT
# =========================================================

@router.post("")
async def chat(request: ChatRequest):

    if not request.message.strip():

        raise HTTPException(
            status_code=400,
            detail="Please describe the workload you want GreenPulse to run."
        )


    workload = build_workload(
        request.message,
        request.carbon_budget
    )


    try:

        result = await run_decision_pipeline(

            workload,

            simulate_grid_failure=(
                request.simulate_grid_failure
            )
        )


        decision = result["result"]


        # =================================================
        # ASSISTANT RESPONSE
        # =================================================

        if decision["decision"] == "REROUTE":

            assistant_message = (

                "🌱 GreenPulse recommends REROUTING this workload.\n\n"

                f"Recommended region: {decision['region']}\n"

                f"Estimated carbon emissions: "
                f"{decision.get('estimated_carbon_g', 'N/A')} g\n\n"

                "The selected region provides a lower-carbon "
                "execution option while satisfying the workload "
                "constraints."
            )


        elif decision["decision"] == "WAIT":

            assistant_message = (

                "⏳ GreenPulse recommends WAITING.\n\n"

                "The current execution window is not the "
                "most carbon-efficient option. A cleaner "
                "execution window is expected within the "
                "allowed deadline."
            )


        elif decision["decision"] == "RUN":

            assistant_message = (

                "🟢 GreenPulse recommends RUNNING the workload now.\n\n"

                f"Execution region: "
                f"{decision.get('region', 'current region')}\n\n"

                "The current execution conditions satisfy "
                "the workload constraints."
            )


        else:

            assistant_message = (

                "⚠️ GreenPulse could not find a feasible "
                "execution plan within the specified constraints.\n\n"

                "Try increasing the carbon budget or allowing "
                "a longer execution deadline."
            )


        # =================================================
        # FINAL RESPONSE
        # =================================================

        return {

            "success": True,

            "message": request.message,

            "assistant_message": assistant_message,

            "scenario": workload["scenario"],

            "workload": workload,

            "decision": decision,

            "ml_predictions": result.get(
                "ml_predictions",
                {}
            ),

            "regions_evaluated": result.get(
                "regions_evaluated",
                []
            )
        }


    except Exception as e:

        raise HTTPException(

            status_code=500,

            detail=str(e)
        )