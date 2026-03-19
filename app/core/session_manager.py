from datetime import datetime


def _empty_draft() -> dict:
    """Return a clean order draft at initial state."""
    return {
        "product_id": None,
        "product_name": None,
        "quantity": None,
        "deadline": None,           # ISO date string e.g. "2026-03-20"
        "custom_fields": {},        # dynamic per-product fields e.g. {"text": "Best Dad Ever"}
        "customer_notes": None,
        "draft_status": "empty",   # empty | product_selected | collecting_details
                                   # | ready_for_confirmation | confirmed
        # Internal runtime fields (prefixed _) — not persisted to DB
        "_required_custom_fields": [],   # list from product_meta.custom_fields
        "_expected_slot": None,          # next slot AI is waiting for (context-aware extraction)
        "_confirmed_order_id": None,
    }


class CallSession:
    def __init__(self, call_id: str, business_id: str, customer_id: str):
        self.call_id = call_id
        self.business_id = business_id
        self.customer_id = customer_id
        self.conversation_history = []   # [{"role": "customer"|"ai", "message": str, "timestamp": str}]
        self.order_draft = _empty_draft()
        self.state = "idle"              # idle | collecting_order | awaiting_confirmation | order_placed
        self.slots_required: list[str] = []
        self.status = "active"
        self.start_time = datetime.utcnow().isoformat()

    def add_message(self, role: str, message: str):
        self.conversation_history.append({
            "role": role,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })

    def update_order_draft(self, fields: dict):
        """Merge fields into the order draft. Handles nested custom_fields correctly."""
        for key, value in fields.items():
            if key == "custom_fields" and isinstance(value, dict):
                self.order_draft["custom_fields"].update(value)
            else:
                self.order_draft[key] = value

    def reset_order_draft(self):
        """Discard the current draft and start fresh."""
        self.order_draft = _empty_draft()
        self.state = "idle"
        self.slots_required = []

    def to_dict(self):
        draft_public = {k: v for k, v in self.order_draft.items() if not k.startswith("_")}
        return {
            "call_id": self.call_id,
            "business_id": self.business_id,
            "customer_id": self.customer_id,
            "conversation_history": self.conversation_history,
            "order_draft": draft_public,
            "state": self.state,
            "slots_required": self.slots_required,
            "status": self.status,
            "start_time": self.start_time,
        }


class SessionManager:
    def __init__(self):
        self.active_sessions: dict[str, CallSession] = {}

    def create_session(self, call_id: str, business_id: str, customer_id: str) -> CallSession:
        session = CallSession(
            call_id=str(call_id),
            business_id=str(business_id),
            customer_id=str(customer_id)
        )
        self.active_sessions[str(call_id)] = session
        print(f"Session created: call_id={call_id}, active_sessions={len(self.active_sessions)}")
        return session

    def get_session(self, call_id: str) -> CallSession | None:
        return self.active_sessions.get(str(call_id))

    def end_session(self, call_id: str):
        call_id = str(call_id)
        if call_id in self.active_sessions:
            del self.active_sessions[call_id]
            print(f"Session ended: call_id={call_id}, active_sessions={len(self.active_sessions)}")

    def active_count(self) -> int:
        return len(self.active_sessions)


# Module-level singleton — shared across all requests in this process
session_manager = SessionManager()
