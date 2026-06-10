"""Push results back to Flow as Actual_Result + verification_status."""
import os

import requests

ACTUAL_KEY = "mKGJdmqWpclHLwA_sBnx4"
STATUS_KEY = "verification_status"


def push_result(requirement_id: str, measured: float, target: float, *,
                lower_is_better: bool = True) -> None:
    passed = measured <= target if lower_is_better else measured >= target
    status = "Passed" if passed else "Failed"

    api = os.environ.get("FLOW_API_URL")
    token = os.environ.get("FLOW_API_TOKEN")
    if not api or not token:
        print(f"[reporter] (dry-run) {requirement_id}: "
              f"actual={measured} target={target} -> {status}")
        return

    payload = {"items": [
        {"id": requirement_id, "key": ACTUAL_KEY, "value": measured},
        {"id": requirement_id, "key": STATUS_KEY, "value": status},
    ]}
    r = requests.post(f"{api}/updateEntityValues", json=payload,
                      headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
