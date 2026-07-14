"""AI layer: Gemini for explanations, Groq for real-time health queries.

Both degrade gracefully: if no API key is set, they return a deterministic
template so the rest of the system (and your tests) still work offline.
"""
from app.config import settings

GEMINI_MODEL = "gemini-flash-latest"
GROQ_MODEL = "openai/gpt-oss-120b"


def gemini_explain(asset_id: str, name: str, prediction: dict) -> str:
    """Turn a model prediction into a plain-English maintenance explanation."""
    prompt = (
        f"You are a maintenance assistant. Explain this prediction in 3-4 sentences "
        f"for a non-technical maintenance manager. Use this exact structure: "
        f"(1) what the prediction is, (2) why the model made it, "
        f"(3) recommended action, (4) urgency.\n\n"
        f"Asset {asset_id} ({name}). Predicted urgency: {prediction['urgency']}. "
        f"Estimated {prediction['predicted_days']} days until maintenance needed. "
        f"Confidence {prediction['confidence']}. "
        f"Telemetry drivers: {prediction['key_features']}."
    )
    if not settings.gemini_api_key:
        return _fallback_explanation(asset_id, name, prediction)
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        return _fallback_explanation(asset_id, name, prediction) + f"  [fallback: {e}]"


def _fallback_explanation(asset_id, name, p) -> str:
    return (
        f"Asset {asset_id} ({name}) is predicted to require maintenance within "
        f"{p['predicted_days']} days (urgency: {p['urgency']}, confidence "
        f"{p['confidence']}). This is driven by its recent telemetry readings. "
        f"Recommended action: schedule a service check "
        f"{'this week' if p['urgency']=='High' else 'in the coming weeks'}."
    )


def groq_health_query(question: str, telemetry_context: str) -> str:
    """Answer a real-time asset-health question given current telemetry."""
    if not settings.groq_api_key:
        return (f"[offline] Based on the provided telemetry:\n{telemetry_context}\n"
                f"Question: {question}")
    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are an asset-health analyst. "
                 "Answer only from the telemetry provided. Be concise."},
                {"role": "user", "content": f"Telemetry:\n{telemetry_context}\n\nQuestion: {question}"},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[groq error: {e}] Telemetry was:\n{telemetry_context}"
