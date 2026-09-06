import re
from collections import defaultdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.decision_service import run_decision_pipeline


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)


# ============================================================
# SESSION MEMORY
# ============================================================
#
# Maximum number of times the exact word "urgent" can be used
# by one chat session = 4.
#
# Example:
# Session A -> urgent -> 1
# Session A -> urgent -> 2
# Session A -> urgent -> 3
# Session A -> urgent -> 4
# Session A -> urgent -> BLOCKED
#
# This is intentionally in-memory for the hackathon prototype.
#
URGENT_USAGE = defaultdict(int)

MAX_URGENT_USES = 4


# ============================================================
# REQUEST MODEL
# ============================================================

class ChatRequest(BaseModel):

    message: str

    # Frontend can send a unique session ID.
    # If it does not, "default" is used.
    session_id: str = "default"

    carbon_budget: float = 120

    simulate_grid_failure: bool = False


# ============================================================
# KEYWORD GROUPS
# ============================================================

URGENT_WORDS = [
    "urgent",
    "emergency",
    "critical",
    "immediately",
    "asap",
    "as soon as possible",
    "right now",
]


REALTIME_WORDS = [
    "real time",
    "realtime",
    "real-time",
    "live",
    "instant",
    "immediate response",
    "low latency",
]


TRAINING_WORDS = [
    "train",
    "training",
    "model training",
    "train model",
    "train an ai",
    "train a model",
    "fine tune",
    "fine-tune",
]


INFERENCE_WORDS = [
    "inference",
    "prediction",
    "predict",
    "classification",
    "recommendation",
    "real time prediction",
]


LARGE_WORKLOAD_WORDS = [
    "huge",
    "massive",
    "large",
    "very large",
    "big dataset",
    "large dataset",
    "large report",
    "massive report",
    "thousands",
    "millions",
    "consolidated",
    "yearly",
    "annual",
    "archive",
    "backup",
]


REPORT_WORDS = [
    "report",
    "document",
    "documents",
    "records",
    "statement",
    "bank statement",
    "financial report",
    "annual report",
    "yearly report",
    "call records",
    "employee records",
]


FLEXIBLE_WORDS = [
    "not urgent",
    "not in a hurry",
    "whenever",
    "flexible",
    "can wait",
    "no rush",
    "low priority",
    "schedule later",
    "later",
    "overnight",
    "off peak",
]


LOW_CARBON_WORDS = [
    "low carbon",
    "lowest carbon",
    "greenest",
    "green",
    "cleanest",
    "carbon efficient",
    "carbon-efficient",
    "minimize emissions",
    "minimum emissions",
    "reduce emissions",
]


RUN_NOW_WORDS = [
    "run now",
    "execute now",
    "start now",
    "run immediately",
    "execute immediately",
]


GRID_FAILURE_WORDS = [
    "grid failure",
    "power failure",
    "power outage",
    "grid outage",
    "electricity outage",
    "server failure",
    "data center failure",
    "datacenter failure",
]


# ============================================================
# HELPERS
# ============================================================

def contains_any(text: str, words: list[str]) -> bool:

    return any(
        word in text
        for word in words
    )


def detect_urgent(message: str) -> bool:

    text = message.lower()

    return contains_any(
        text,
        URGENT_WORDS
    )


# ============================================================
# WORKLOAD TYPE
# ============================================================

def detect_workload_type(message: str):

    text = message.lower()

    if contains_any(text, TRAINING_WORDS):

        return "training"

    if contains_any(text, INFERENCE_WORDS):

        return "inference"

    if contains_any(text, REPORT_WORDS):

        return "batch"

    return "batch"


# ============================================================
# WORKLOAD SIZE
# ============================================================

def detect_workload_size(message: str):

    text = message.lower()

    # --------------------------------------------------------
    # Pages
    # --------------------------------------------------------

    page_match = re.search(
        r"(\d+(?:,\d+)?)\s*(?:pages?|page)",
        text
    )

    if page_match:

        pages = int(
            page_match.group(1).replace(",", "")
        )

        if pages >= 10000:
            return 1500

        if pages >= 5000:
            return 1000

        if pages >= 1000:
            return 700

        if pages >= 500:
            return 400

        if pages >= 100:
            return 250

        return 150


    # --------------------------------------------------------
    # Records / rows / entries / employees
    # --------------------------------------------------------

    record_match = re.search(
        r"(\d+(?:,\d+)?)\s*"
        r"(?:records?|rows?|entries?|employees?)",
        text
    )

    if record_match:

        records = int(
            record_match.group(1).replace(",", "")
        )

        if records >= 1000000:
            return 1500

        if records >= 100000:
            return 1000

        if records >= 10000:
            return 700

        if records >= 5000:
            return 500

        if records >= 1000:
            return 300

        return 150


    # --------------------------------------------------------
    # Keyword based size
    # --------------------------------------------------------

    if any(
        word in text
        for word in [
            "massive",
            "huge dataset",
            "huge report",
            "massive report",
            "millions",
            "thousands",
        ]
    ):

        return 800


    if contains_any(
        text,
        LARGE_WORKLOAD_WORDS
    ):

        return 500


    return 100


# ============================================================
# EXPLICIT RUNTIME
# ============================================================

def extract_runtime(message: str):

    text = message.lower()

    match = re.search(
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:hours?|hrs?|hr)",
        text
    )

    if match:

        return float(
            match.group(1)
        )

    return None


# ============================================================
# EXPLICIT DEADLINE
# ============================================================

def extract_deadline(message: str):

    text = message.lower()

    match = re.search(
        r"deadline\s*"
        r"(?:of|is|within|:)?\s*"
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:hours?|hrs?|hr)",
        text
    )

    if match:

        return float(
            match.group(1)
        )


    match = re.search(
        r"(?:within|in)\s+"
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:hours?|hrs?|hr)",
        text
    )

    if match:

        return float(
            match.group(1)
        )

    return None


# ============================================================
# RUNTIME ESTIMATION
# ============================================================

def estimate_runtime(
    message: str,
    workload_type: str,
    workload_size: int
):

    explicit = extract_runtime(message)

    if explicit is not None:

        return explicit


    text = message.lower()


    if contains_any(
        text,
        REALTIME_WORDS
    ):

        return 1


    if detect_urgent(message):

        return 1


    if workload_type == "training":

        if workload_size >= 1000:
            return 16

        if workload_size >= 700:
            return 12

        if workload_size >= 400:
            return 8

        return 4


    if workload_type == "inference":

        return 1


    if workload_size >= 1000:

        return 12

    if workload_size >= 700:

        return 10

    if workload_size >= 500:

        return 8

    if workload_size >= 300:

        return 6

    if workload_size >= 200:

        return 4


    return 2


# ============================================================
# DEADLINE ESTIMATION
# ============================================================

def estimate_deadline(
    message: str,
    workload_type: str,
    runtime_hours: float
):

    explicit = extract_deadline(message)

    if explicit is not None:

        return max(
            runtime_hours,
            explicit
        )


    text = message.lower()


    if detect_urgent(message):

        return max(
            1,
            runtime_hours
        )


    if contains_any(
        text,
        REALTIME_WORDS
    ):

        return max(
            1,
            runtime_hours
        )


    if contains_any(
        text,
        FLEXIBLE_WORDS
    ):

        return max(
            24,
            runtime_hours * 3
        )


    if workload_type == "training":

        return max(
            24,
            runtime_hours * 2
        )


    if runtime_hours >= 10:

        return 24

    if runtime_hours >= 6:

        return 18

    if runtime_hours >= 4:

        return 12


    return max(
        8,
        runtime_hours * 2
    )


# ============================================================
# PRIORITY
# ============================================================

def detect_priority(message: str):

    text = message.lower()

    if detect_urgent(message):

        return "urgent"


    if any(
        word in text
        for word in [
            "critical",
            "emergency",
            "immediately",
            "asap",
            "as soon as possible",
        ]
    ):

        return "high"


    if any(
        word in text
        for word in [
            "low priority",
            "not urgent",
            "not in a hurry",
            "no rush",
            "whenever",
            "flexible",
        ]
    ):

        return "low"


    return "normal"


# ============================================================
# LOCATION DETECTION
# ============================================================

def detect_location(message: str):

    text = message.lower()

    location_map = {

        "india": "IN",
        "indian": "IN",

        "germany": "DE",
        "german": "DE",

        "france": "FR",
        "french": "FR",

        "united kingdom": "GB",
        "uk": "GB",
        "britain": "GB",
        "british": "GB",

        "uae": "AE",
        "united arab emirates": "AE",

        "saudi arabia": "SA",
        "saudi": "SA",

        "israel": "IL",

        "poland": "PL",

        "czech republic": "CZ",
        "czechia": "CZ",

        "hungary": "HU",

        "romania": "RO",
    }


    for keyword, zone in location_map.items():

        if keyword in text:

            return zone


    return None


# ============================================================
# LOCATION INTENT
# ============================================================

def detect_location_intent(message: str):

    requested = detect_location(message)

    if requested:

        return {
            "requested": True,
            "zone": requested
        }


    if detect_urgent(message):

        return {
            "requested": True,
            "zone": "IN",
            "reason":
                "Urgent workload defaults to an India preference."
        }


    return {
        "requested": False,
        "zone": None
    }


# ============================================================
# SCHEDULING INTENT
# ============================================================

def detect_schedule_preference(message: str):

    text = message.lower()

    if contains_any(
        text,
        RUN_NOW_WORDS
    ):

        return "now"


    if contains_any(
        text,
        FLEXIBLE_WORDS
    ):

        return "flexible"


    if "schedule" in text:

        return "flexible"


    return "automatic"


# ============================================================
# CARBON PREFERENCE
# ============================================================

def detect_carbon_preference(message: str):

    text = message.lower()

    if contains_any(
        text,
        LOW_CARBON_WORDS
    ):

        return "lowest_carbon"


    if (
        detect_workload_size(message) >= 500
        and detect_schedule_preference(message)
        == "flexible"
    ):

        return "lowest_carbon"


    return "balanced"


# ============================================================
# GRID FAILURE
# ============================================================

def detect_grid_failure(message: str):

    text = message.lower()

    return contains_any(
        text,
        GRID_FAILURE_WORDS
    )


# ============================================================
# WORKLOAD INTERPRETATION
# ============================================================

def interpret_workload(message: str):

    workload_type = detect_workload_type(
        message
    )

    workload_size = detect_workload_size(
        message
    )

    runtime_hours = estimate_runtime(
        message,
        workload_type,
        workload_size
    )

    deadline_hours = estimate_deadline(
        message,
        workload_type,
        runtime_hours
    )

    priority = detect_priority(
        message
    )

    location_intent = detect_location_intent(
        message
    )

    schedule_preference = detect_schedule_preference(
        message
    )

    carbon_preference = detect_carbon_preference(
        message
    )

    grid_failure = detect_grid_failure(
        message
    )


    if (
        priority == "urgent"
        or contains_any(
            message.lower(),
            REALTIME_WORDS
        )
    ):

        latency_tolerance = 120

    elif workload_type == "inference":

        latency_tolerance = 150

    else:

        latency_tolerance = 300


    return {

        "workload_type":
            workload_type,

        "workload_size":
            workload_size,

        "runtime_hours":
            runtime_hours,

        "deadline_hours":
            deadline_hours,

        "priority":
            priority,

        "latency_tolerance":
            latency_tolerance,

        "requested_region":
            location_intent.get("zone"),

        "schedule_preference":
            schedule_preference,

        "carbon_preference":
            carbon_preference,

        "grid_failure_detected":
            grid_failure,
    }


# ============================================================
# ASSISTANT MESSAGE
# ============================================================

def build_assistant_message(
    decision,
    workload,
    regions_evaluated
):

    decision_type = decision.get(
        "decision",
        "UNKNOWN"
    )

    region = decision.get(
        "region"
    )

    carbon = decision.get(
        "estimated_carbon_g"
    )

    saved = decision.get(
        "carbon_saved_g"
    )

    start_minutes = decision.get(
        "start_in_minutes",
        0
    )

    reason = decision.get(
        "reason",
        ""
    )


    # ========================================================
    # REROUTE
    # ========================================================

    if decision_type == "REROUTE":

        message = (
            "🌱 GreenPulse recommends REROUTE.\n\n"
            f"Execution region: {region}.\n"
        )


        if carbon is not None:

            message += (
                f"Estimated carbon: {carbon:.2f} g.\n"
            )


        if saved is not None:

            message += (
                f"Estimated carbon saved: "
                f"{saved:.2f} g.\n"
            )


        if reason:

            message += (
                f"Reason: {reason}"
            )


        return message


    # ========================================================
    # WAIT
    # ========================================================

    if decision_type == "WAIT":

        if start_minutes:

            if start_minutes >= 60:

                hours = start_minutes // 60

                message = (
                    "⏳ GreenPulse recommends WAIT.\n\n"
                    f"The cleaner execution window begins "
                    f"in approximately {hours} hour(s)."
                )

            else:

                message = (
                    "⏳ GreenPulse recommends WAIT.\n\n"
                    f"The cleaner execution window begins "
                    f"in approximately {start_minutes} minute(s)."
                )

        else:

            message = (
                "⏳ GreenPulse recommends waiting "
                "for a cleaner execution window."
            )


        if carbon is not None:

            message += (
                f"\nEstimated scheduled carbon: "
                f"{carbon:.2f} g."
            )


        if saved is not None:

            message += (
                f"\nEstimated carbon saved: "
                f"{saved:.2f} g."
            )


        if reason:

            message += (
                f"\n\nReason: {reason}"
            )


        return message


    # ========================================================
    # RUN
    # ========================================================

    if decision_type == "RUN":

        message = (
            "▶️ GreenPulse recommends RUNNING "
            "the workload now.\n\n"
        )


        if region:

            message += (
                f"Execution region: {region}.\n"
            )


        if carbon is not None:

            message += (
                f"Estimated carbon: {carbon:.2f} g."
            )


        if reason:

            message += (
                f"\n\nReason: {reason}"
            )


        return message


    # ========================================================
    # NO FEASIBLE PLAN
    # ========================================================

    return (
        "⚠️ GreenPulse could not find a feasible "
        "execution plan.\n\n"
        f"Reason: "
        f"{reason or 'No region satisfies the current constraints.'}"
    )


# ============================================================
# CHAT ENDPOINT
# ============================================================

@router.post("")
async def chat(request: ChatRequest):

    message = request.message.strip()


    # ========================================================
    # EMPTY PROMPT
    # ========================================================

    if not message:

        raise HTTPException(
            status_code=400,
            detail=(
                "Please describe the AI workload "
                "you want GreenPulse to allocate."
            )
        )


    text = message.lower()


    # ========================================================
    # URGENT LIMIT — MAXIMUM 4 PER SESSION
    # ========================================================
    #
    # IMPORTANT:
    #
    # We count only the exact standalone word "urgent".
    #
    # urgent      -> counted
    # URGENT      -> counted
    # Urgent      -> counted
    # urgently    -> NOT counted
    # urgency     -> NOT counted
    #
    # The counter belongs to request.session_id.
    #
    # Therefore different users/sessions have separate limits.
    #

    urgent_count_in_message = len(
        re.findall(
            r"\burgent\b",
            text,
            flags=re.IGNORECASE
        )
    )


    session_id = request.session_id.strip()

    if not session_id:

        session_id = "default"


    current_usage = URGENT_USAGE[
        session_id
    ]


    # --------------------------------------------------------
    # BLOCK if this message would exceed 4
    # --------------------------------------------------------

    if (
        current_usage
        + urgent_count_in_message
        > MAX_URGENT_USES
    ):

        remaining = max(
            0,
            MAX_URGENT_USES - current_usage
        )


        raise HTTPException(
            status_code=400,
            detail=(
                "⚠️ Urgent usage limit reached.\n\n"
                "The word 'urgent' can be used "
                "a maximum of 4 times per chat session.\n\n"
                f"Uses remaining: {remaining}."
            )
        )


    # --------------------------------------------------------
    # Record usage ONLY after validation
    # --------------------------------------------------------

    URGENT_USAGE[
        session_id
    ] += urgent_count_in_message


    # ========================================================
    # INTERPRET WORKLOAD
    # ========================================================

    interpreted = interpret_workload(
        message
    )


    # ========================================================
    # GRID FAILURE
    # ========================================================

    simulate_failure = (
        request.simulate_grid_failure
        or interpreted[
            "grid_failure_detected"
        ]
    )


    # ========================================================
    # URGENT HANDLING
    # ========================================================

    priority = interpreted[
        "priority"
    ]

    if priority == "urgent":

        interpreted[
            "deadline_hours"
        ] = max(
            1,
            interpreted[
                "runtime_hours"
            ]
        )


    # ========================================================
    # FLEXIBLE WORKLOAD
    # ========================================================

    if (
        interpreted[
            "schedule_preference"
        ]
        == "flexible"
    ):

        interpreted[
            "deadline_hours"
        ] = max(
            interpreted[
                "deadline_hours"
            ],
            24
        )


    # ========================================================
    # CARBON BUDGET
    # ========================================================

    carbon_budget = request.carbon_budget


    if interpreted[
        "carbon_preference"
    ] == "lowest_carbon":

        carbon_budget = min(
            carbon_budget,
            120
        )


    # ========================================================
    # CREATE WORKLOAD
    # ========================================================

    workload = {

        "workload_type":
            interpreted[
                "workload_type"
            ],

        "runtime_hours":
            interpreted[
                "runtime_hours"
            ],

        "deadline_hours":
            interpreted[
                "deadline_hours"
            ],

        "latency_tolerance":
            interpreted[
                "latency_tolerance"
            ],

        "carbon_budget":
            carbon_budget,

        "priority":
            interpreted[
                "priority"
            ],

        "workload_size":
            interpreted[
                "workload_size"
            ],

        "requested_region":
            interpreted[
                "requested_region"
            ],

        "schedule_preference":
            interpreted[
                "schedule_preference"
            ],

        "carbon_preference":
            interpreted[
                "carbon_preference"
            ],

        "grid_failure_detected":
            interpreted[
                "grid_failure_detected"
            ],
    }


    # ========================================================
    # RUN REAL DECISION PIPELINE
    # ========================================================

    try:

        result = await run_decision_pipeline(

            workload,

            simulate_grid_failure=(
                simulate_failure
            )
        )


        decision = result.get(
            "result",
            {}
        )


        # ====================================================
        # ASSISTANT RESPONSE
        # ====================================================

        assistant_message = build_assistant_message(

            decision,

            workload,

            result.get(
                "regions_evaluated",
                []
            )
        )


        # ====================================================
        # LOCATION INFORMATION
        # ====================================================

        requested_region = interpreted[
            "requested_region"
        ]


        if requested_region == "IN":

            assistant_message += (
                "\n\n"
                "📍 Location preference detected: IN."
                "\nIndia was selected as the preferred "
                "origin region for this prototype request."
            )


        # ====================================================
        # WORKLOAD SUMMARY
        # ====================================================

        assistant_message += (

            "\n\n"
            "Workload analysis:\n"

            f"• Type: "
            f"{interpreted['workload_type']}\n"

            f"• Estimated size: "
            f"{interpreted['workload_size']}\n"

            f"• Runtime: "
            f"{interpreted['runtime_hours']:g} hour(s)\n"

            f"• Scheduling window: "
            f"{interpreted['deadline_hours']:g} hour(s)\n"

            f"• Priority: "
            f"{interpreted['priority']}\n"

            f"• Scheduling mode: "
            f"{interpreted['schedule_preference']}\n"

            f"• Carbon preference: "
            f"{interpreted['carbon_preference']}"
        )


        # ====================================================
        # LIVE REGION SUMMARY
        # ====================================================

        regions = result.get(
            "regions_evaluated",
            []
        )


        if regions:

            assistant_message += (

                "\n\n🌍 Live regions evaluated: "

                + ", ".join(

                    str(
                        region.get(
                            "name",
                            region.get(
                                "zone",
                                "?"
                            )
                        )
                    )

                    for region in regions
                )
            )


        # ====================================================
        # URGENT COUNTER
        # ====================================================

        current_urgent_usage = URGENT_USAGE[
            session_id
        ]

        urgent_remaining = max(
            0,
            MAX_URGENT_USES
            - current_urgent_usage
        )


        # ====================================================
        # RESPONSE
        # ====================================================

        return {

            "success": True,

            "assistant_message":
                assistant_message,

            "message":
                assistant_message,

            "workload":
                workload,

            "decision":
                decision,

            "ml_predictions":
                result.get(
                    "ml_predictions",
                    {}
                ),

            "regions_evaluated":
                regions,

            "estimated_energy_kwh":
                result.get(
                    "estimated_energy_kwh"
                ),

            "urgent_used":
                current_urgent_usage,

            "urgent_remaining":
                urgent_remaining,

            "interpretation": {

                "workload_type":
                    interpreted[
                        "workload_type"
                    ],

                "workload_size":
                    interpreted[
                        "workload_size"
                    ],

                "runtime_hours":
                    interpreted[
                        "runtime_hours"
                    ],

                "deadline_hours":
                    interpreted[
                        "deadline_hours"
                    ],

                "priority":
                    interpreted[
                        "priority"
                    ],

                "requested_region":
                    interpreted[
                        "requested_region"
                    ],

                "schedule_preference":
                    interpreted[
                        "schedule_preference"
                    ],

                "carbon_preference":
                    interpreted[
                        "carbon_preference"
                    ],

                "grid_failure":
                    interpreted[
                        "grid_failure_detected"
                    ],
            }
        }


    except Exception as e:

        print(
            "GreenPulse chat error:",
            repr(e)
        )


        raise HTTPException(

            status_code=500,

            detail=(
                "GreenPulse could not process "
                "the workload decision.\n\n"
                f"Backend error: {str(e)}"
            )
        )