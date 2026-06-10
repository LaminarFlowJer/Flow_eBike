"""Push results back to Flow as Actual_Result.

The Flow customer API is multi-tenant: every request needs a ``customer``
header (tenant slug) and an ``X-API-Key`` header. Values are written with
``PUT /project/{projectId}/entities/values/batch``. ``verification_status`` is
computed by Flow from Actual_Result vs the requirement's pass/fail criteria, so
this module never writes it directly.

Configure via environment:
  FLOW_API_BASE   e.g. https://backend.branch.flowengineering.com
  FLOW_CUSTOMER   tenant slug, e.g. jeremiah
  FLOW_API_KEY    brd_... customer API key
  FLOW_PROJECT_ID project UUID
"""
import os

import requests

# Data-model attribute key for the "Actual_Result" field.
ACTUAL_KEY = "mKGJdmqWpclHLwA_sBnx4"


def _config() -> dict | None:
    base = os.environ.get("FLOW_API_BASE")
    customer = os.environ.get("FLOW_CUSTOMER")
    api_key = os.environ.get("FLOW_API_KEY")
    project_id = os.environ.get("FLOW_PROJECT_ID")
    if not all((base, customer, api_key, project_id)):
        return None
    return {"base": base, "customer": customer, "api_key": api_key,
            "project_id": project_id}


def push_results(results: list[tuple[str, float]]) -> None:
    """Write Actual_Result for each (requirement_id, measured) pair.

    ``measured`` must already be in the requirement's own unit (the same unit as
    its target ``value``), so Flow's auto-calculated status compares correctly.
    """
    cfg = _config()
    if cfg is None:
        for req_id, measured in results:
            print(f"[reporter] (dry-run) {req_id}: Actual_Result={measured}")
        return

    payload = {"updates": [
        {"entityId": req_id, "key": ACTUAL_KEY, "value": measured}
        for req_id, measured in results
    ]}
    url = f"{cfg['base']}/project/{cfg['project_id']}/entities/values/batch"
    r = requests.put(
        url, json=payload, timeout=30,
        headers={"customer": cfg["customer"], "X-API-Key": cfg["api_key"]},
    )
    r.raise_for_status()


def push_result(requirement_id: str, measured: float) -> None:
    """Convenience wrapper for a single requirement."""
    push_results([(requirement_id, measured)])
