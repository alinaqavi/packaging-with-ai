from flask import Flask, request, jsonify
from flask_cors import CORS
import re, traceback
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --------------------------------------------------
# 🧩 CONFIG / SAMPLE PRODUCTS
# --------------------------------------------------
PRODUCT_MAP = {
    "paper_cup": {"name": "Paper Cup"},
    "paper_bag": {"name": "Paper Bag"},
    "meal_box": {"name": "Meal Box"},
    "pizza_box": {"name": "Pizza Box"},
    "sandwich_box": {"name": "Sandwich Box"},
    "burger_box": {"name": "Burger Box"},
    "popcorn_holder": {"name": "Popcorn Holder"},
    "paper_tray": {"name": "Paper Tray"},
}

# In-memory session storage
SESSIONS = {}


# --------------------------------------------------
# 🧰 HELPERS
# --------------------------------------------------
def ensure_session(session_id: str):
    """Ensure or create session state."""
    if not session_id:
        session_id = "anon"
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "session_id": session_id,
            "selected_product": None,
            "color": None,
            "logo_uploaded": False,
            "history": [],
            "last_action": None,
        }
    return SESSIONS[session_id]


def now_ts():
    """UTC timestamp"""
    return datetime.utcnow().isoformat()


def detect_intent_and_entities(text: str):
    """
    Lightweight rule-based intent + entity detection.
    Returns (intent, entities)
    """
    msg = (text or "").lower()
    entities = {}

    # Product selection
    for pid, meta in PRODUCT_MAP.items():
        if pid in msg or meta["name"].lower() in msg:
            entities["product_id"] = pid
            return "select_product", entities

    # Color selection
    hex_match = re.search(r"(#(?:[0-9a-f]{3}|[0-9a-f]{6}))", msg)
    if hex_match:
        entities["color"] = hex_match.group(1)
        return "set_color", entities
    for color in ["red", "blue", "green", "black", "white", "yellow", "pink", "orange", "brown", "purple"]:
        if f" {color}" in f" {msg}":
            entities["color"] = color
            return "set_color", entities

    # Generate mockup
    if any(k in msg for k in ["generate", "make mockup", "create mockup", "generate mockup", "mockup"]):
        return "generate_mockup", entities

    # Edit mockup
    if any(k in msg for k in ["edit", "change", "remove background", "make it", "glossy", "matte", "brighter", "darker"]):
        entities["edit_text"] = text
        return "edit_mockup", entities

    # Upload logo
    if "upload logo" in msg or "logo uploaded" in msg:
        return "upload_logo", entities

    # Info
    if any(k in msg for k in ["help", "who are you", "about", "how to", "what can you do"]):
        return "info", entities

    # Default
    return "default", entities


# --------------------------------------------------
# 💬 CHATBOT ENDPOINT
# --------------------------------------------------
@app.route("/send_chat", methods=["POST"])
def send_chat():
    """
    Chat endpoint
    Request:
        { "session_id": "...", "message": "..." }
    Response:
        { "message": "...", "action": {...}, "session_state": {...} }
    """
    try:
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id", "anon")
        user_msg = (data.get("message") or "").strip()

        session = ensure_session(session_id)
        session["history"].append({"role": "user", "content": user_msg, "ts": now_ts()})

        intent, entities = detect_intent_and_entities(user_msg)
        reply = ""
        action = None

        # --------------------------
        # INTENT HANDLING
        # --------------------------
        if intent == "select_product":
            pid = entities.get("product_id")
            if pid in PRODUCT_MAP:
                session["selected_product"] = pid
                reply = f"✅ Selected product: *{PRODUCT_MAP[pid]['name']}*."
                action = {"type": "select_product", "product_id": pid}
            else:
                reply = "I couldn’t find that product. Try: 'select paper cup'."

        elif intent == "set_color":
            color = entities["color"]
            session["color"] = color
            reply = f"🎨 Color set to **{color}**."
            action = {"type": "set_color", "color": color}

        elif intent == "generate_mockup":
            if not session["selected_product"]:
                reply = "Please select a product first (e.g., 'select paper bag')."
            else:
                product = PRODUCT_MAP[session["selected_product"]]["name"]
                reply = f"Generating mockup for *{product}*."
                action = {"type": "generate_mockup", "product_id": session["selected_product"], "color": session.get("color")}

        elif intent == "edit_mockup":
            if not session["selected_product"]:
                reply = "Please select and generate a mockup first."
            else:
                edit_text = entities.get("edit_text", user_msg)
                reply = f"Applying edit: *{edit_text}*."
                action = {"type": "edit_mockup", "prompt": edit_text}

        elif intent == "upload_logo":
            session["logo_uploaded"] = True
            reply = "Got it 👍 — logo uploaded flag set."
            action = {"type": "logo_uploaded"}

        elif intent == "info":
            reply = "I'm your packaging mockup chatbot. I can select products, set colors, generate mockups, and apply edits."

        else:
            reply = "You can say: 'select paper bag', 'make it blue', or 'generate mockup'."

        # Update session
        session["history"].append({"role": "assistant", "content": reply, "ts": now_ts()})
        session["last_action"] = action

        return jsonify({
            "session_id": session_id,
            "message": reply,
            "action": action,
            "session_state": {
                "product": session.get("selected_product"),
                "color": session.get("color"),
                "logo_uploaded": session.get("logo_uploaded"),
                "history_length": len(session["history"])
            }
        })

    except Exception as e:
        print("send_chat error:", e)
        traceback.print_exc()
        return jsonify({"error": "chat failed"}), 500


# --------------------------------------------------
# 🧭 SESSION MGMT ROUTES
# --------------------------------------------------
@app.route("/session/<sid>")
def get_session(sid):
    return jsonify(SESSIONS.get(sid, {"error": "not found"}))

@app.route("/sessions")
def list_sessions():
    return jsonify(list(SESSIONS.keys()))

@app.route("/reset/<sid>", methods=["POST"])
def reset_session(sid):
    if sid in SESSIONS:
        del SESSIONS[sid]
    return jsonify({"ok": True, "session_id": sid})


# --------------------------------------------------
# 🏠 HOME ROUTE
# --------------------------------------------------
@app.route("/", methods=["GET"])
def chatbot_home():
    return "🤖 Chatbot ready — send POST /send_chat with { 'message': 'select paper cup' }"


# --------------------------------------------------
# 🚀 RUN SERVER
# --------------------------------------------------
if __name__ == "__main__":
    print("✅ Mockup Chatbot Server running on http://127.0.0.1:8080")
    app.run(host="0.0.0.0", port=8080, debug=True)
