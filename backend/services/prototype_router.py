import os
import re
import math
import pandas as pd


# ============================================================
# DATASET LOCATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATASET_PATH = os.path.join(
    BASE_DIR,
    "data",
    "greenpulse_carbon_dataset.xlsx"
)


# ============================================================
# LOAD DATASET
# ============================================================

try:

    DATA = pd.read_excel(DATASET_PATH)

    DATA["datetime"] = pd.to_datetime(
        DATA["datetime"],
        errors="coerce"
    )

    DATA["carbon_intensity"] = pd.to_numeric(
        DATA["carbon_intensity"],
        errors="coerce"
    )

    DATA = DATA.dropna(
        subset=[
            "location",
            "region",
            "zone",
            "carbon_intensity"
        ]
    )

except Exception as e:

    print(
        f"[GreenPulse] Dataset loading failed: {e}"
    )

    DATA = pd.DataFrame()


# ============================================================
# INDIA / REGION INFORMATION
# ============================================================

INDIA_LOCATIONS = {
    "Delhi": {
        "zone": "IN-NO",
        "priority": 1
    },

    "Mumbai": {
        "zone": "IN-WE",
        "priority": 2
    },

    "Hyderabad": {
        "zone": "IN-WE",
        "priority": 3
    }
}


# ============================================================
# KEYWORD GROUPS
# ============================================================

URGENT_WORDS = [
    "urgent",
    "emergency",
    "immediately",
    "immediate",
    "critical",
    "critical task",
    "right now",
    "asap",
    "real time",
    "realtime",
    "live",
    "instant",
    "instant response"
]


LARGE_WORKLOAD_WORDS = [
    "5000 page",
    "5000 pages",
    "large dataset",
    "huge dataset",
    "massive dataset",
    "big dataset",
    "million",
    "millions",
    "yearly",
    "annual",
    "consolidated",
    "bulk",
    "archive",
    "records",
    "historical",
    "large report",
    "long report",
    "bank statement",
    "employee",
    "employees",
    "payroll",
    "financial report"
]


BATCH_WORDS = [
    "batch",
    "overnight",
    "background",
    "report",
    "summary",
    "summarize",
    "summarise",
    "analysis",
    "analyse",
    "analyze",
    "processing",
    "process",
    "dataset"
]


TRAINING_WORDS = [
    "train",
    "training",
    "model training",
    "fine tune",
    "fine-tune",
    "finetune"
]


INFERENCE_WORDS = [
    "inference",
    "prediction",
    "predict",
    "classification",
    "detect",
    "recognize",
    "recognition"
]


WAIT_WORDS = [
    "can wait",
    "flexible",
    "no rush",
    "overnight",
    "later",
    "schedule",
    "scheduled",
    "deadline tomorrow",
    "within 24 hours",
    "within 48 hours"
]


GRID_FAILURE_WORDS = [
    "grid failure",
    "power outage",
    "outage",
    "server failure",
    "data center failure",
    "datacenter failure",
    "unavailable",
    "down",
    "failed",
    "failure",
    "blackout"
]


LOW_CARBON_WORDS = [
    "green",
    "greenest",
    "cleanest",
    "low carbon",
    "lowest carbon",
    "low emission",
    "lowest emission",
    "sustainable",
    "carbon efficient",
    "carbon-efficient"
]


# ============================================================
# TEXT HELPERS
# ============================================================

def contains_any(text, words):

    return any(
        word in text
        for word in words
    )


# ============================================================
# WORKLOAD CLASSIFICATION
# ============================================================

def classify_workload(message):

    text = message.lower()

    urgent = contains_any(
        text,
        URGENT_WORDS
    )

    large = contains_any(
        text,
        LARGE_WORKLOAD_WORDS
    )

    batch = contains_any(
        text,
        BATCH_WORDS
    )

    training = contains_any(
        text,
        TRAINING_WORDS
    )

    inference = contains_any(
        text,
        INFERENCE_WORDS
    )

    wait_allowed = contains_any(
        text,
        WAIT_WORDS
    )

    grid_problem = contains_any(
        text,
        GRID_FAILURE_WORDS
    )

    low_carbon_requested = contains_any(
        text,
        LOW_CARBON_WORDS
    )


    # --------------------------------------------------------
    # Explicit numeric clues
    # --------------------------------------------------------

    page_match = re.search(
        r"(\d[\d,]*)\s*(?:page|pages)",
        text
    )

    pages = None

    if page_match:

        pages = int(
            page_match.group(1).replace(",", "")
        )


    employee_match = re.search(
        r"(\d[\d,]*)\s*(?:employees|employee)",
        text
    )

    employees = None

    if employee_match:

        employees = int(
            employee_match.group(1).replace(",", "")
        )


    if pages and pages >= 1000:

        large = True


    if employees and employees >= 500:

        large = True


    # --------------------------------------------------------
    # Determine workload type
    # --------------------------------------------------------

    if training:

        workload_type = "training"

    elif inference:

        workload_type = "inference"

    else:

        workload_type = "batch"


    # --------------------------------------------------------
    # Priority
    # --------------------------------------------------------

    if urgent:

        priority = "urgent"

    elif large:

        priority = "large"

    else:

        priority = "normal"


    # --------------------------------------------------------
    # Runtime estimate
    # --------------------------------------------------------

    if large:

        runtime_hours = 4.0

    elif training:

        runtime_hours = 6.0

    elif inference:

        runtime_hours = 0.5

    else:

        runtime_hours = 2.0


    # --------------------------------------------------------
    # Deadline
    # --------------------------------------------------------

    if urgent:

        deadline_hours = 1.0

    elif wait_allowed or large:

        deadline_hours = 24.0

    else:

        deadline_hours = 8.0


    # --------------------------------------------------------
    # Latency tolerance
    # --------------------------------------------------------

    if urgent:

        latency_tolerance = 50

    elif inference:

        latency_tolerance = 100

    elif large:

        latency_tolerance = 500

    else:

        latency_tolerance = 150


    return {

        "workload_type": workload_type,

        "priority": priority,

        "urgent": urgent,

        "large": large,

        "wait_allowed": wait_allowed,

        "grid_problem": grid_problem,

        "low_carbon_requested": low_carbon_requested,

        "runtime_hours": runtime_hours,

        "deadline_hours": deadline_hours,

        "latency_tolerance": latency_tolerance,

        "pages": pages,

        "employees": employees

    }


# ============================================================
# DATASET SERVER SNAPSHOT
# ============================================================

def get_server_snapshot():

    if DATA.empty:

        return []


    # Latest observation for every provider/region/location
    latest_time = DATA["datetime"].max()

    latest = DATA[
        DATA["datetime"] == latest_time
    ].copy()


    # If something goes wrong with timestamps,
    # fall back to latest row per location.

    if latest.empty:

        latest = (
            DATA
            .sort_values("datetime")
            .groupby(
                [
                    "provider",
                    "region",
                    "location",
                    "zone"
                ],
                as_index=False
            )
            .tail(1)
        )


    latest = (
        latest
        .sort_values("carbon_intensity")
        .drop_duplicates(
            subset=[
                "provider",
                "region",
                "location",
                "zone"
            ]
        )
    )


    servers = []


    for _, row in latest.iterrows():

        servers.append({

            "provider": str(row["provider"]),

            "region": str(row["region"]),

            "location": str(row["location"]),

            "zone": str(row["zone"]),

            "carbon_intensity": float(
                row["carbon_intensity"]
            ),

            "timestamp": str(
                row["datetime"]
            )

        })


    return servers


# ============================================================
# SERVER AVAILABILITY
# ============================================================

def simulated_availability(server, profile):

    location = server["location"].lower()

    message_type = profile.get(
        "priority",
        "normal"
    )


    # Emergency workloads:
    # keep Indian local options available,
    # but simulate some non-local capacity pressure.

    if profile["urgent"]:

        if location in [
            "Delhi",
            "Mumbai",
            "Hyderabad"
        ]:

            return True


    # Large workloads:
    # simulate that some regions have limited capacity.

    if profile["large"]:

        high_carbon = (
            server["carbon_intensity"] > 500
        )

        if high_carbon:

            return False


    # Grid failure simulation

    if profile["grid_problem"]:

        # Simulate failure of the user's local region.

        if location in [
            "Delhi",
            "Mumbai",
            "Hyderabad"
        ]:

            return False


    return True


# ============================================================
# INDIA LOCALITY
# ============================================================

def india_candidates(servers):

    candidates = []

    for server in servers:

        if server["location"] in INDIA_LOCATIONS:

            candidates.append(server)

    return candidates


# ============================================================
# SELECT SERVER
# ============================================================

def select_server(
    message,
    profile
):

    servers = get_server_snapshot()


    if not servers:

        return {

            "decision": "NO FEASIBLE PLAN",

            "reason": "Carbon dataset is unavailable.",

            "region": None

        }


    # --------------------------------------------------------
    # Filter unavailable servers
    # --------------------------------------------------------

    available = [

        server
        for server in servers

        if simulated_availability(
            server,
            profile
        )

    ]


    if not available:

        if profile["wait_allowed"]:

            return {

                "decision": "WAIT",

                "region": None,

                "location": None,

                "reason":
                    "Current capacity is constrained. "
                    "The workload can be scheduled "
                    "for a later execution window.",

                "estimated_carbon_g": None

            }


        return {

            "decision": "NO FEASIBLE PLAN",

            "region": None,

            "location": None,

            "reason":
                "No available execution location "
                "satisfies the current constraints.",

            "estimated_carbon_g": None

        }


    # --------------------------------------------------------
    # URGENT / EMERGENCY
    # --------------------------------------------------------

    if profile["urgent"]:

        india = india_candidates(
            available
        )


        if india:

            # Choose the cleanest available
            # Indian location.

            selected = min(
                india,
                key=lambda x:
                x["carbon_intensity"]
            )


            return {

                "decision": "RUN",

                "region": selected["region"],

                "location": selected["location"],

                "zone": selected["zone"],

                "provider": selected["provider"],

                "carbon_intensity":
                    selected["carbon_intensity"],

                "estimated_carbon_g":
                    round(
                        selected["carbon_intensity"]
                        * 0.8
                        * profile["runtime_hours"],
                        2
                    ),

                "reason":
                    "Urgent workload detected. "
                    "GreenPulse prioritised a nearby "
                    "Indian execution location while "
                    "respecting carbon intensity."

            }


    # --------------------------------------------------------
    # LARGE / FLEXIBLE WORKLOAD
    # --------------------------------------------------------

    if profile["large"]:

        selected = min(
            available,
            key=lambda x:
            x["carbon_intensity"]
        )


        estimated = round(
            selected["carbon_intensity"]
            * 0.8
            * profile["runtime_hours"],
            2
        )


        # If a cleaner server is available but
        # workload is flexible, demonstrate WAIT.

        if profile["wait_allowed"]:

            return {

                "decision": "WAIT",

                "region": selected["region"],

                "location": selected["location"],

                "zone": selected["zone"],

                "provider": selected["provider"],

                "carbon_intensity":
                    selected["carbon_intensity"],

                "estimated_carbon_g":
                    estimated,

                "reason":
                    "Large batch workload detected. "
                    "Because the workload is flexible, "
                    "GreenPulse can schedule it during "
                    "a cleaner execution window."

            }


        return {

            "decision": "REROUTE",

            "region": selected["region"],

            "location": selected["location"],

            "zone": selected["zone"],

            "provider": selected["provider"],

            "carbon_intensity":
                selected["carbon_intensity"],

            "estimated_carbon_g":
                estimated,

            "reason":
                "Large workload detected. "
                "GreenPulse selected the lowest-carbon "
                "available dataset-backed execution location."

        }


    # --------------------------------------------------------
    # NORMAL WORKLOAD
    # --------------------------------------------------------

    selected = min(
        available,
        key=lambda x:
        x["carbon_intensity"]
    )


    estimated = round(
        selected["carbon_intensity"]
        * 0.8
        * profile["runtime_hours"],
        2
    )


    return {

        "decision": "REROUTE",

        "region": selected["region"],

        "location": selected["location"],

        "zone": selected["zone"],

        "provider": selected["provider"],

        "carbon_intensity":
            selected["carbon_intensity"],

        "estimated_carbon_g":
            estimated,

        "reason":
            "GreenPulse compared available "
            "dataset-backed execution locations "
            "and selected a lower-carbon option."

    }


# ============================================================
# MAIN PROTOTYPE FUNCTION
# ============================================================

def prototype_decision(message):

    profile = classify_workload(
        message
    )

    result = select_server(
        message,
        profile
    )


    # --------------------------------------------------------
    # Add workload interpretation
    # --------------------------------------------------------

    result["workload_profile"] = profile

    result["data_source"] = (
        "greenpulse_carbon_dataset.xlsx"
    )

    result["data_mode"] = (
        "historical_dataset_simulation"
    )


    return result