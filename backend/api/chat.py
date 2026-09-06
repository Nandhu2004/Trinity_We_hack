import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.decision_service import run_decision_pipeline


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)


# =========================================================
# URGENT WORD LIMIT
# =========================================================

URGENT_LIMIT = 4

# Stores usage separately for each browser/session.
# Example:
# {
#     "session-A": 2,
#     "session-B": 4
# }
urgent_usage = {}


# =========================================================
# REQUEST MODEL
# =========================================================

class ChatRequest(BaseModel):

    message: str

    # Frontend generates this automatically.
    session_id: str = "default"

    carbon_budget: float = 100

    simulate_grid_failure: bool = False


# =========================================================
# WORKLOAD TYPE DETECTION
# =========================================================

def detect_workload_type(message: str):

    text = message.lower()

    if "training" in text or "train" in text:
        return "training"

    if "inference" in text:
        return "inference"

    return "batch"


# =========================================================
# RUNTIME + DEADLINE EXTRACTION
# =========================================================

def extract_workload_values(message: str):

    text = message.lower()

    runtime_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)",
        text
    )

    deadline_match = re.search(
        r"deadline\s*(?:of|is|:)?\s*"
        r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)",
        text
    )

    runtime_hours = (
        float(runtime_match.group(1))
        if runtime_match
        else None
    )

    deadline_hours = (
        float(deadline_match.group(1))
        if deadline_match
        else None
    )

    return runtime_hours, deadline_hours


# =========================================================
# URGENT WORD CHECK
# =========================================================

def check_urgent_limit(session_id: str, message: str):

    text = message.lower()

    # Count only the complete word "urgent".
    #
    # urgent       -> counts
    # URGENT       -> counts
    # Urgent       -> counts
    # urgently     -> does NOT count
    # urgency      -> does NOT count

    urgent_count = len(
        re.findall(r"\burgent\b", text)
    )

    # Create counter for new session
    if session_id not in urgent_usage:
        urgent_usage[session_id] = 0

    current_count = urgent_usage[session_id]

    # No urgent word in this message
    if urgent_count == 0:

        return True, current_count


    # Check whether this message would exceed 4
    if current_count + urgent_count > URGENT_LIMIT:

        return False, current_count


    # Update usage
    urgent_usage[session_id] = (
        current_count + urgent_count
    )

    return True, urgent_usage[session_id]


# =========================================================
# CHAT ENDPOINT
# =========================================================

@router.post("")
async def chat(request: ChatRequest):

    # -----------------------------------------------------
    # CHECK URGENT LIMIT FIRST
    # -----------------------------------------------------

    allowed, urgent_count = check_urgent_limit(
        request.session_id,
        request.message
    )

    if not allowed:

        raise HTTPException(
            status_code=429,
            detail=(
                "Urgent request limit reached. "
                "You can use the word 'urgent' a maximum "
                "of 4 times per session."
            )
        )


    # -----------------------------------------------------
    # DETECT WORKLOAD
    # -----------------------------------------------------

    workload_type = detect_workload_type(
        request.message
    )


    # -----------------------------------------------------
    # EXTRACT RUNTIME + DEADLINE
    # -----------------------------------------------------

    runtime_hours, deadline_hours = (
        extract_workload_values(
            request.message
        )
    )


    # -----------------------------------------------------
    # DEFAULT VALUES
    #
    # This allows simple judge/demo prompts such as:
    #
    # "I need to summarize a large dataset"
    #
    # instead of forcing the user to specify hours.
    # -----------------------------------------------------

    if runtime_hours is None:

        text = request.message.lower()

        if any(
            word in text
            for word in [
                "urgent",
                "emergency",
                "immediate",
                "immediately",
                "critical"
            ]
        ):

            runtime_hours = 1

        elif any(
            word in text
            for word in [
                "large",
                "huge",
                "5000",
                "thousand",
                "yearly",
                "annual",
                "consolidated",
                "report"
            ]
        ):

            runtime_hours = 6

        else:

            runtime_hours = 2


    if deadline_hours is None:

        text = request.message.lower()

        if any(
            word in text
            for word in [
                "urgent",
                "emergency",
                "immediate",
                "immediately",
                "critical"
            ]
        ):

            deadline_hours = 2

        elif any(
            word in text
            for word in [
                "large",
                "huge",
                "5000",
                "thousand",
                "yearly",
                "annual",
                "consolidated",
                "report"
            ]
        ):

            deadline_hours = 24

        else:

            deadline_hours = 24


    # -----------------------------------------------------
    # PRIORITY
    # -----------------------------------------------------

    text = request.message.lower()

    if any(
        word in text
        for word in [
            "urgent",
            "emergency",
            "critical",
            "immediate",
            "immediately"
        ]
    ):

        priority = "urgent"

    elif any(
        word in text
        for word in [
            "high priority",
            "important"
        ]
    ):

        priority = "high"

    else:

        priority = "normal"


    # -----------------------------------------------------
    # WORKLOAD SIZE
    # -----------------------------------------------------

    workload_size = 100

    if any(
        word in text
        for word in [
            "large",
            "huge",
            "5000",
            "thousand",
            "massive",
            "yearly",
            "annual",
            "consolidated"
        ]
    ):

        workload_size = 1000


    # -----------------------------------------------------
    # WORKLOAD OBJECT
    # -----------------------------------------------------

    workload = {

        "workload_type": workload_type,

        "runtime_hours": runtime_hours,

        "deadline_hours": deadline_hours,

        "latency_tolerance": 150,

        "carbon_budget": request.carbon_budget,

        "priority": priority,

        "workload_size": workload_size
    }


    # -----------------------------------------------------
    # RUN DECISION PIPELINE
    # -----------------------------------------------------

    try:

        result = await run_decision_pipeline(

            workload,

            simulate_grid_failure=(
                request.simulate_grid_failure
            )
        )


        decision = result["result"]


        # -------------------------------------------------
        # CREATE AI RESPONSE
        # -------------------------------------------------

        if decision["decision"] == "REROUTE":

            assistant_message = (

                "🌱 GreenPulse recommends REROUTING "
                f"this workload to {decision['region']}.\n\n"

                "Reason: this region provides a "
                "lower-carbon execution option under "
                "the current workload constraints."
            )


        elif decision["decision"] == "WAIT":

            assistant_message = (

                "⏳ GreenPulse recommends WAITING "
                "for a cleaner execution window.\n\n"

                "The workload can meet its deadline "
                "more efficiently by avoiding the "
                "current carbon conditions."
            )


        elif decision["decision"] == "RUN":

            assistant_message = (

                "▶️ GreenPulse recommends RUNNING "
                "the workload now.\n\n"

                "The current execution option satisfies "
                "the workload constraints."
            )


        else:

            assistant_message = (

                "⚠️ GreenPulse could not find a feasible "
                "execution plan within the given constraints."
            )


        # -------------------------------------------------
        # RETURN RESPONSE
        # -------------------------------------------------

        return {

            "success": True,

            "message": request.message,

            "assistant_message": assistant_message,

            "urgent_usage": urgent_count,

            "urgent_limit": URGENT_LIMIT,

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