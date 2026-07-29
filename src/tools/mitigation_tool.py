from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# Finalized Tool-Feasible Mitigation Policy Table, from
# cybersecurity_lead_complete_package.md section 2.
# Bands are (min_confidence, action, tool_function, guardrail_note), checked
# highest threshold first. Defence Impairment intentionally has a lower
# high-confidence bar (>=0.70) than the other 3 attack classes (>=0.85) —
# it is critical severity and the Cybersecurity Lead's policy treats waiting
# for higher confidence on it as itself a risk.
POLICY = {
    "Normal": [
        (0.0, "log_only", "tool_log_telemetry_event", "Zero state mutation. Always safe."),
    ],
    "Storage Exhaustion": [
        (0.85, "flush_command_queue + App Restart", "tool_flush_queue_and_restart_app",
         "Verify watchdog timer active prior to process restart."),
        (0.70, "flush_command_queue", "tool_flush_command_queue",
         "Preserve priority egress telemetry."),
        (0.0, "log_only", "tool_log_telemetry_event", "No autonomous state mutation."),
    ],
    "Command Flooding": [
        (0.85, "flush_command_queue + Rate Limit", "tool_rate_limit_uplink",
         "Keep emergency ground command channel unthrottled."),
        (0.70, "flush_command_queue", "tool_flush_command_queue",
         "Log dropped command count for audit trail."),
        (0.0, "log_only", "tool_log_telemetry_event", "Guardrail triggered (<0.70)."),
    ],
    "Data Injection": [
        (0.85, "isolate_subsystem", "tool_isolate_subsystem",
         "Maintain core CDH flight bus operational."),
        (0.70, "isolate_subsystem + Ground Review", "tool_isolate_subsystem_soft",
         "FP guardrail: avoid hard power cutoff on this class under noise."),
        (0.0, "log_only", "tool_log_telemetry_event", "No autonomous isolation."),
    ],
    "Defence Impairment": [
        (0.70, "enable_safe_mode", "tool_enable_safe_mode",
         "Critical severity. Immediate escalation. Auto-dispatch emergency beacon frame."),
        (0.0, "Escalate Alert", "tool_dispatch_urgent_beacon",
         "Ground controller manual intervention required."),
    ],
}


def decide_mitigation(class_name: str, confidence: float) -> dict:
    if class_name not in POLICY:
        return {"error": f"No policy defined for class '{class_name}'"}

    for threshold, action, tool_function, guardrail_note in POLICY[class_name]:
        if confidence >= threshold:
            return {
                "class_name": class_name,
                "confidence": confidence,
                "action": action,
                "tool_function": tool_function,
                "guardrail_note": guardrail_note,
                "autonomous": action != "Escalate Alert",
            }
    return {"error": "unreachable"}


class MitigationQuery(BaseModel):
    class_name: str = Field(..., description="The detected attack class name from the Classifier Agent.")
    confidence: float = Field(..., description="The Classifier Agent's confidence score (0.0-1.0).")


class MitigationPolicyTool(BaseTool):
    name: str = "decide_mitigation"
    description: str = (
        "Looks up the exact, deterministic mitigation action for a detected attack "
        "class and confidence score, per the finalized Cybersecurity Lead policy. "
        "This decision is fixed policy — do not override or second-guess it."
    )
    args_schema: type[BaseModel] = MitigationQuery

    def _run(self, class_name: str, confidence: float) -> dict:
        return decide_mitigation(class_name, confidence)
