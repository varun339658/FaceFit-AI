"""
skin_explainer_service.py — Skin Condition Explainer via Groq LLaMA 3.3 70B + RAG
"""
import os, json, re
from langchain_groq import ChatGroq
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import Chroma
try:
    from langchain_huggingface import HuggingFaceEmbeddings as Embeddings
except:
    from langchain_community.embeddings import SentenceTransformerEmbeddings as Embeddings

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.2, groq_api_key=GROQ_API_KEY)

_ret = None
try:
    _docs = TextLoader("rag_data/skincare_knowledge.txt").load()
    _chunks = CharacterTextSplitter(chunk_size=600, chunk_overlap=100).split_documents(_docs)
    _emb = Embeddings(model_name="paraphrase-MiniLM-L3-v2")
    _vs = Chroma.from_documents(_chunks, _emb, collection_name="explainer_v1")
    _ret = _vs.as_retriever(search_kwargs={"k": 6})
except Exception as e:
    print(f"Explainer RAG init: {e}")

def _rag_ctx(query):
    if not _ret: return ""
    try: return "\n\n".join(d.page_content for d in _ret.invoke(query))
    except: return ""

def _extract_json(text):
    text = text.strip()
    try: return json.loads(text)
    except: pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try: return json.loads(m.group())
        except: pass
    return {}

def generate_condition_explanations(conditions, skin_tone, severity_counts=None):
    severity_counts = severity_counts or {}
    seen, unique = set(), []
    for c in conditions:
        k = c.lower().strip()
        if k and k not in seen: seen.add(k); unique.append(k)
    if not unique: unique = ["normal skin"]
    conditions_str = ", ".join(unique)
    rag_ctx = _rag_ctx(f"skin conditions {conditions_str} causes treatment ingredients {skin_tone}")
    sev_parts = []
    for cond, count in severity_counts.items():
        sev = "mild" if count <= 2 else "moderate" if count <= 5 else "severe"
        sev_parts.append(f"{cond}: {count} ({sev})")
    sev_ctx = ("SEVERITY: " + ", ".join(sev_parts)) if sev_parts else ""

    prompt = f"""Board-certified dermatologist explaining skin to patient in India.
Detected: {conditions_str} | Skin: {skin_tone} | {sev_ctx}
RAG: {rag_ctx}

Return ONLY valid JSON:
{{
  "explanations": {{
    "<condition>": {{
      "what_it_is": "1 clear sentence",
      "why_you_have_it": "1-2 sentences for {skin_tone} skin in India",
      "severity": "mild|moderate|severe",
      "key_ingredient": "single most effective ingredient",
      "avoid": ["3 ingredients/products to avoid"],
      "good_for_you": ["3 evidence-based ingredients with why"],
      "lifestyle_tip": "1 actionable tip"
    }}
  }},
  "global_warnings": ["2-3 cross-condition warnings"],
  "priority_condition": "<most urgent>",
  "summary": "2-3 warm encouraging sentences"
}}"""
    try:
        resp = llm.invoke(prompt)
        raw = resp.content if hasattr(resp,"content") else str(resp)
        data = _extract_json(raw)
        if data and "explanations" in data: return data
    except Exception as e:
        print(f"Explainer LLM error: {e}")
    return _fallback(unique, skin_tone, severity_counts)

def _fallback(conditions, skin_tone, severity_counts):
    STATIC = {
        "acne": {"what_it_is":"Acne occurs when hair follicles clog with oil and dead skin cells.","why_you_have_it":f"{'Dark' if skin_tone=='dark' else skin_tone.title()} skin is prone to acne due to overactive sebaceous glands and Indian humidity.","severity":"mild","key_ingredient":"Salicylic Acid 2% BHA","avoid":["Coconut oil","Heavy cream moisturizers","Physical scrubs"],"good_for_you":["Salicylic Acid 2% — dissolves pore oil","Niacinamide 10% — reduces inflammation","Benzoyl Peroxide 2.5% — kills bacteria"],"lifestyle_tip":"Change pillowcase every 2-3 days and reduce dairy intake."},
        "dark circle": {"what_it_is":"Dark circles are discoloration under eyes from thin skin and blood vessel visibility.","why_you_have_it":"Common in Indian skin tones due to genetics, dehydration, and screen time.","severity":"mild","key_ingredient":"Caffeine + Peptide Eye Cream","avoid":["Eye rubbing","Fragranced eye creams","Sleeping with makeup"],"good_for_you":["Caffeine — reduces puffiness","Vitamin K — strengthens vessels","Retinol 0.025% — thickens skin"],"lifestyle_tip":"Sleep 7-8 hours with head slightly elevated and drink 3L water daily."},
        "dark spot": {"what_it_is":"Dark spots are patches of excess melanin from sun damage, acne marks, or hormones.","why_you_have_it":f"{'Dark' if skin_tone=='dark' else skin_tone.title()} skin is especially prone to PIH (post-inflammatory hyperpigmentation).","severity":"mild","key_ingredient":"Vitamin C 15% + Alpha Arbutin","avoid":["Unprotected sun exposure","Picking scabs","Harsh scrubs"],"good_for_you":["Vitamin C 15% — inhibits melanin","Alpha Arbutin — gentle fading","Azelaic Acid 10% — reduces PIH"],"lifestyle_tip":"Never skip SPF 50 — sun exposure is #1 cause of darkening."},
    }
    explanations = {}
    for cond in conditions:
        cond_lower = cond.lower()
        matched = next((v for k, v in STATIC.items() if k in cond_lower), None)
        if matched:
            matched = dict(matched)
            sc = severity_counts.get("acne_count", 0) if "acne" in cond_lower else 1
            matched["severity"] = "mild" if sc <= 2 else "moderate" if sc <= 5 else "severe"
            explanations[cond] = matched
        else:
            explanations[cond] = {"what_it_is":f"Detected skin condition: {cond}.","why_you_have_it":"Genetics, environment, and lifestyle.","severity":"mild","key_ingredient":"Niacinamide","avoid":["Harsh actives","Sun exposure"],"good_for_you":["Niacinamide","Hyaluronic Acid","SPF 50"],"lifestyle_tip":"Maintain routine and stay hydrated."}
    return {"explanations": explanations, "global_warnings":["Use SPF 50 daily","Patch test new products","Avoid mixing actives without guidance"],"priority_condition": conditions[0] if conditions else "normal","summary": f"Detected: {', '.join(conditions)}. With right ingredients significant improvement is possible in 4-8 weeks."}