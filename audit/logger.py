import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "audit_trail.json")


class AuditLogger:
    """Append-only structured JSON audit trail generator for AI agent transaction safety."""
    
    def __init__(self, log_path: str = LOG_FILE_PATH):
        self.log_path = log_path
        self._ensure_log_file()

    def _ensure_log_file(self):
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump([], f)

    def log_event(
        self,
        event_type: str,
        tool_name: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        reasoning: str = "",
        status: str = "SUCCESS",
        merchant_id: str = "rzp_merchant_001"
    ) -> Dict[str, Any]:
        """Record an immutable tool call or decision event to the audit trail log."""
        record = {
            "event_id": f"evt_{int(time.time() * 1000)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "merchant_id": merchant_id,
            "event_type": event_type,  # e.g., "QUERY", "AVAILABILITY_CHECK", "SPEND_GUARDRAIL", "CHECKOUT", "ERROR"
            "tool_name": tool_name,
            "reasoning": reasoning,
            "status": status,
            "inputs": inputs,
            "outputs": outputs
        }

        try:
            logs = self.get_all_logs()
            logs.append(record)
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            print(f"[AuditLogger Error] Could not write to audit log: {e}")

        return record

    def get_all_logs(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.log_path):
            return []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def generate_summary(self) -> str:
        logs = self.get_all_logs()
        if not logs:
            return "No audit logs available."
            
        summary_lines = ["# Audit Trail Summary\n"]
        for idx, entry in enumerate(logs[-10:], 1):  # Last 10 events
            summary_lines.append(
                f"{idx}. [{entry['timestamp']}] **{entry['event_type']}** via `{entry['tool_name']}` | "
                f"Status: **{entry['status']}** | Reasoning: *{entry['reasoning']}*"
            )
        return "\n".join(summary_lines)


audit_logger = AuditLogger()
