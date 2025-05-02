from datetime import datetime
from firebase_admin import firestore

def log_prompt_usage(db, user_email, prompt, models):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    doc_id = f"{user_email}_{today}"
    doc_ref = db.collection("daily_usage").document(doc_id)

    doc = doc_ref.get()
    data = doc.to_dict() if doc.exists else {}

    prompt_key = prompt.strip()
    existing = data.get("prompts", {}).get(prompt_key, {"models": [], "llm_calls": 0})

    updated_models = list(set(existing["models"] + models))
    updated_calls = existing["llm_calls"] + 1

    doc_ref.set({
        "user_email": user_email,
        "date": today,
        "last_updated": firestore.SERVER_TIMESTAMP,
        "prompts": {
            **data.get("prompts", {}),
            prompt_key: {
                "models": updated_models,
                "llm_calls": updated_calls
            }
        }
    }, merge=True)
