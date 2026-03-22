from __future__ import annotations
from dotenv import load_dotenv
load_dotenv() # This line reads your .env file

import argparse
import json
import os
from pathlib import Path
import re
import unicodedata
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

# ---- New imports for retry logic, OpenAI & Ollama ----
import time
from functools import wraps
from openai import OpenAI
import ollama # <-- Added for Ollama

# Optional dependencies are loaded defensively
np = None
sentence_model = None
RAPIDFUZZ_AVAILABLE = False
NLP_AVAILABLE = False
USE_SCISPACY = False

# ---- LLM clients ----
openai_client = None
ollama_client = None
OLLAMA_MODEL = "llama3" # Default Ollama model

# ---- Optional vector & fuzzy libs ----
try:
    import numpy as np
except Exception:
    np = None

try:
    from sentence_transformers import SentenceTransformer
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception:
    sentence_model = None

try:
    from rapidfuzz import process, fuzz
    RAPIDFUZZ_AVAILABLE = True
except Exception:
    RAPIDFUZZ_AVAILABLE = False

# ---- NLP pipelines (SciSpaCy preferred) ----
try:
    import spacy
    try:
        nlp = spacy.load("en_ner_bc5cdr_md")
        USE_SCISPACY = True
    except Exception:
        nlp = spacy.load("en_core_web_sm")
    NLP_AVAILABLE = True
except Exception:
    nlp = None
    NLP_AVAILABLE = False

# ---- Initialize LLM Clients ----
try:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        openai_client = OpenAI(api_key=openai_api_key)
except Exception:
    pass # openai_client remains None

try:
    # Check if the Ollama service is running before initializing the client
    ollama.ps()
    ollama_client = ollama.Client()
except Exception:
    # This is not an error, just means Ollama isn't available
    pass # ollama_client remains None


# ---- Paths (adjust if needed) ----
def get_dataset_path(filename: str) -> str:
    # Try current directory
    local_path = Path(filename)
    if local_path.exists():
        return str(local_path.absolute())
    
    # Try user's Downloads directory
    home_downloads = Path.home() / "Downloads" / filename
    if home_downloads.exists():
        return str(home_downloads.absolute())
    
    # Fallback to the hardcoded path from the original code
    return rf"C:\Users\ayush\Downloads\{filename}"

SIDDHA_PATH = get_dataset_path("NATIONAL SIDDHA MORBIDITY CODES.xls")
UNANI_PATH  = get_dataset_path("NATIONAL UNANI MORBIDITY CODES.xls")
MERGED_PATH = get_dataset_path("merged_dataset.xlsx")

# =========================
# NEW: Retry Decorator
# =========================
def retry_with_backoff(retries=5, initial_delay=1, backoff_factor=2):
    """A decorator for retrying a function with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for i in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    # More robust check for retryable errors
                    if any(err in error_str for err in ["rate limit", "429", "resource has been exhausted", "connectionerror"]):
                        print(f"API/Connection error. Retrying in {delay:.2f}s... (Attempt {i + 1}/{retries})")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        raise e
            raise Exception(f"Function {func.__name__} failed after {retries} retries.")
        return wrapper
    return decorator

# =========================
# Excel reading
# =========================
def read_excel_smart(path: Union[str, Path]) -> pd.DataFrame:
    """Read .xls with xlrd and .xlsx with openpyxl to avoid engine errors."""
    path = str(path)
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xls":
        return pd.read_excel(path, engine="xlrd")
    return pd.read_excel(path, engine="openpyxl")

# =========================
# Normalization helpers
# (No changes in this section)
# =========================
def normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d.columns = (
        d.columns
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )
    colmap = {}
    if "namc_code" in d.columns: colmap["namc_code"] = "namc_code"
    if "numc_code" in d.columns: colmap["numc_code"] = "numc_code"
    if "namc_term" in d.columns: colmap["namc_term"] = "namc_term"
    if "numc_term" in d.columns: colmap["numc_term"] = "numc_term"
    if "short_definition" in d.columns: colmap["short_definition"] = "short_definition"
    if "sidha_code" in d.columns: colmap["sidha_code"] = "siddha_code"
    if "siddha_code" in d.columns: colmap["siddha_code"] = "siddha_code"
    if "unani_code" in d.columns: colmap["unani_code"] = "unani_code"
    return d.rename(columns=colmap)

def normalize_text(s: str) -> str:
    if s is None: return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.split())

def _series_or_empty(df: pd.DataFrame, col: str) -> pd.Series:
    if col in df.columns: return df[col].astype(str)
    return pd.Series([""] * len(df), index=df.index, dtype="object")

# =========================
# Dataset preparation
# (No changes in this section)
# =========================
def prepare_siddha(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = normalize_headers(df_raw)
    need_any = ("short_definition" in df.columns) or ("namc_term" in df.columns)
    if not need_any or ("namc_code" not in df.columns): raise ValueError("Siddha sheet must contain NAMC_CODE and at least one of Short_definition/NAMC_TERM")
    df = df.copy()
    df["__text"] = _series_or_empty(df, "short_definition")
    empty_mask = df["__text"].str.strip().eq("")
    df.loc[empty_mask, "__text"] = _series_or_empty(df, "namc_term")
    df["__norm"] = df["__text"].map(normalize_text)
    df["__discipline"] = "Siddha"
    df["__code_str"] = df["namc_code"].astype(str).str.strip()
    df = df[df["__norm"] != ""]
    return df

def prepare_unani(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = normalize_headers(df_raw)
    need_any = ("short_definition" in df.columns) or ("numc_term" in df.columns)
    if not need_any or ("numc_code" not in df.columns): raise ValueError("Unani sheet must contain NUMC_CODE and at least one of Short_definition/NUMC_TERM")
    df = df.copy()
    df["__text"] = _series_or_empty(df, "short_definition")
    empty_mask = df["__text"].str.strip().eq("")
    df.loc[empty_mask, "__text"] = _series_or_empty(df, "numc_term")
    df["__norm"] = df["__text"].map(normalize_text)
    df["__discipline"] = "Unani"
    df["__code_str"] = df["numc_code"].astype(str).str.strip()
    df = df[df["__norm"] != ""]
    return df

def build_search_space(sid: pd.DataFrame, una: pd.DataFrame) -> pd.DataFrame:
    return pd.concat([sid, una], ignore_index=True)

# =========================
# Matching utilities
# (No changes in this section)
# =========================
def find_exact(base: pd.DataFrame, q_norm: str) -> Optional[pd.Series]:
    hits = base[base["__norm"] == q_norm]
    return hits.iloc[0] if not hits.empty else None

def find_partial(base: pd.DataFrame, q_norm: str) -> Optional[pd.Series]:
    hits = base[base["__norm"].str.contains(q_norm, na=False, regex=False)]
    return hits.iloc[0] if not hits.empty else None

def find_fuzzy(base: pd.DataFrame, q_norm: str, top_k: int = 5, threshold: int = 85) -> List[Tuple[str, float, int]]:
    if not RAPIDFUZZ_AVAILABLE or base.empty: return []
    choices = base["__norm"].tolist()
    results = process.extract(q_norm, choices, scorer=fuzz.token_sort_ratio, limit=top_k)
    return [(c, float(score), int(idx)) for (c, score, idx) in results if score >= threshold]

def pick_row_by_index(base: pd.DataFrame, idx: int) -> Optional[pd.Series]:
    if idx < 0 or idx >= len(base): return None
    return base.iloc[idx]

# =========================
# Merged mapping
# (No changes in this section)
# =========================
def prepare_merged(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = normalize_headers(df_raw)
    need_cols = ("siddha_code" in df.columns) or ("unani_code" in df.columns)
    if not need_cols: raise ValueError("Merged sheet must contain Siddha_code and/or Unani_code columns")
    for c in ("siddha_code", "unani_code"):
        if c in df.columns: df[c] = df[c].astype(str).str.strip()
    return df

def lookup_merged(merged: pd.DataFrame, discipline: str, code_str: str) -> Optional[pd.Series]:
    if merged is None or merged.empty: return None
    col = "siddha_code" if discipline == "Siddha" and "siddha_code" in merged.columns else "unani_code" if "unani_code" in merged.columns else None
    if not col: return None
    m = merged[merged[col].astype(str).str.strip() == str(code_str).strip()]
    return m.iloc[0] if not m.empty else None

def make_result(row: pd.Series, merged_row: Optional[pd.Series], suggestions: Optional[List[Dict]] = None) -> Dict:
    return {"discipline": row["__discipline"], "code": row["__code_str"], "label": row["__text"], "merged": merged_row.to_dict() if merged_row is not None else None, "suggestions": suggestions or []}

# =========================
# Core search
# (No changes in this section)
# =========================
def search_disease(disease_name: str, siddha_df: pd.DataFrame, unani_df: pd.DataFrame, merged_df: pd.DataFrame, fuzzy_top_k: int = 5, fuzzy_threshold: int = 85) -> Dict:
    q_norm = normalize_text(disease_name)
    sid = prepare_siddha(siddha_df)
    una = prepare_unani(unani_df)
    base = build_search_space(sid, una)
    row = find_exact(base, q_norm)
    if row is not None:
        m = lookup_merged(merged_df, row["__discipline"], row["__code_str"])
        return make_result(row, m)
    row = find_partial(base, q_norm)
    if row is not None:
        m = lookup_merged(merged_df, row["__discipline"], row["__code_str"])
        return make_result(row, m)
    suggestions_out: List[Dict] = []
    for choice, score, idx in find_fuzzy(base, q_norm, top_k=fuzzy_top_k, threshold=fuzzy_threshold):
        srow = pick_row_by_index(base, idx)
        if srow is not None:
            suggestions_out.append({"discipline": srow["__discipline"], "code": srow["__code_str"], "label": srow["__text"], "score": score})
    if suggestions_out:
        return {"error": "No exact/partial match; showing fuzzy suggestions", "suggestions": suggestions_out}
    return {"error": "No match found in Siddha or Unani."}

# =========================
# NLP / LLM enhancements
# =========================
def _parse_llm_json(raw_text: str) -> Optional[dict]:
    if not raw_text:
        return None
    try:
        # Accommodate potential markdown code blocks from some models
        clean_text = re.sub(r"^```json\s*|\s*```$", "", raw_text.strip(), flags=re.DOTALL)
        return json.loads(clean_text)
    except Exception:
        return None

def extract_medical_entities(text: str) -> Dict[str, Union[List[str], bool, str]]:
    text_l = (text or "").strip()
    if not NLP_AVAILABLE or not text_l: return {"symptoms": [text_l] if text_l else [], "body_parts": [], "conditions": [], "enhanced": False}
    try:
        doc = nlp(text_l)
        entities = {"symptoms": [], "body_parts": [], "conditions": [], "enhanced": True}
        for ent in getattr(doc, "ents", []):
            label = ent.label_.upper()
            txt = ent.text.strip().lower()
            if label in {"DISEASE"}:
                entities["conditions"].append(txt)
        if not entities["symptoms"] and not entities["conditions"]:
            entities["symptoms"] = [text_l.lower()]
        return entities
    except Exception as e:
        return {"symptoms": [text_l] if text_l else [], "body_parts": [], "conditions": [], "enhanced": False, "error": str(e)}

@retry_with_backoff(retries=5, initial_delay=1, backoff_factor=2)
def enhance_query_with_openai(user_input: str) -> Dict[str, Union[str, bool, List[str]]]:
    """Use OpenAI to expand the user's query into structured JSON fields."""
    if openai_client is None:
        return {"original": user_input, "enhanced": False, "error": "OpenAI client not configured."}

    system_prompt = (
        "You are an expert in traditional medicine (Ayurveda, Siddha, Unani). "
        "Analyze the patient's description and return a JSON object with keys: "
        "'primary_symptoms', 'related_symptoms', 'possible_conditions', "
        "'recommended_system', 'severity', and 'search_terms'. Return only the valid JSON object."
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f'A patient describes: "{user_input}"'}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        raw_json_string = response.choices[0].message.content
        parsed = _parse_llm_json(raw_json_string)

        if isinstance(parsed, dict):
            parsed["enhanced"] = True
            return parsed
        return {"original": user_input, "enhanced": False, "raw_response": raw_json_string}
    except Exception as e:
        return {"original": user_input, "enhanced": False, "error": str(e)}


@retry_with_backoff(retries=5, initial_delay=1, backoff_factor=2)
def enhance_query_with_ollama(user_input: str, model_name: str = OLLAMA_MODEL) -> Dict[str, Union[str, bool, List[str]]]:
    """
    Use a local Ollama model to expand the user's query into structured JSON.
    """
    if ollama_client is None:
        return {"original": user_input, "enhanced": False, "error": "Ollama client not available."}

    system_prompt = (
        "You are an expert in traditional medicine (Ayurveda, Siddha, Unani). "
        "Analyze the patient's description and return a JSON object with the following keys: "
        "'primary_symptoms' (list of strings), "
        "'related_symptoms' (list of strings), "
        "'possible_conditions' (list of strings of likely traditional medicine conditions), "
        "'recommended_system' (string: 'Ayurveda', 'Siddha', or 'Unani'), "
        "'severity' (string: 'mild', 'moderate', or 'severe'), "
        "'search_terms' (list of strings of alternative terms to search in a database). "
        "Return only the valid JSON object and nothing else."
    )

    try:
        response = ollama_client.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f'A patient describes: "{user_input}"'}
            ],
            format="json" # This tells Ollama to ensure the output is valid JSON
        )
        raw_json_string = response['message']['content']
        parsed = _parse_llm_json(raw_json_string)

        if isinstance(parsed, dict):
            parsed["enhanced"] = True
            return parsed
        return {"original": user_input, "enhanced": False, "raw_response": raw_json_string}
    except Exception as e:
        return {"original": user_input, "enhanced": False, "error": str(e)}


@retry_with_backoff(retries=3, initial_delay=0.5, backoff_factor=2)
def semantic_search(query: str, base: pd.DataFrame, top_k: int = 5) -> List[Tuple[int, float]]:
    if sentence_model is None or np is None or base.empty: return []
    q_emb = sentence_model.encode([query])
    texts = base["__norm"].tolist()
    t_embs = sentence_model.encode(texts)
    sims = np.dot(q_emb, t_embs.T)[0]
    if top_k < len(sims):
        top_indices = np.argpartition(sims, -top_k)[-top_k:]
    else:
        top_indices = np.arange(len(sims))
    sorted_indices = top_indices[np.argsort(sims[top_indices])][::-1]
    return [(int(idx), float(sims[idx])) for idx in sorted_indices if sims[idx] > 0.5]


def intelligent_search_disease(
    disease_name: str,
    siddha_df: pd.DataFrame,
    unani_df: pd.DataFrame,
    merged_df: pd.DataFrame,
    fuzzy_top_k: int = 5,
    fuzzy_threshold: int = 85,
    llm_provider: Optional[str] = None,
    ollama_model: str = OLLAMA_MODEL,
    use_llm: bool = False
) -> Dict:
    # If use_llm is true, pick a default provider if none was specified
    if use_llm and not llm_provider:
        if openai_client:
            llm_provider = 'openai'
        elif ollama_client:
            llm_provider = 'ollama'
    traditional_result = search_disease(
        disease_name, siddha_df, unani_df, merged_df, fuzzy_top_k, fuzzy_threshold
    )

    # If we get a direct hit, we can still enhance it with LLM insights
    if "error" not in traditional_result:
        result = traditional_result.copy()
        if llm_provider == 'openai' and openai_client:
            llm_analysis = enhance_query_with_openai(disease_name)
            result["llm_insights"] = llm_analysis
            result["search_method"] = "traditional_enhanced_openai"
        elif llm_provider == 'ollama' and ollama_client:
            llm_analysis = enhance_query_with_ollama(disease_name, model_name=ollama_model)
            result["llm_insights"] = llm_analysis
            result["search_method"] = "traditional_enhanced_ollama"
        else:
            result["search_method"] = "traditional"
        return result

    # If no LLM is selected, return the basic fuzzy/error result
    if not llm_provider:
        return traditional_result

    try:
        entities = extract_medical_entities(disease_name)
        llm_analysis = {}

        if llm_provider == 'openai' and openai_client:
            llm_analysis = enhance_query_with_openai(disease_name)
            search_method = "intelligent_openai"
        elif llm_provider == 'ollama' and ollama_client:
            llm_analysis = enhance_query_with_ollama(disease_name, model_name=ollama_model)
            search_method = "intelligent_ollama"
        else:
            # Fallback if a provider was requested but is unavailable
            return traditional_result

        sid = prepare_siddha(siddha_df)
        una = prepare_unani(unani_df)
        base = build_search_space(sid, una)
        q_norm = normalize_text(disease_name)
        semantic_matches = semantic_search(q_norm, base, top_k=fuzzy_top_k)

        enhanced_suggestions: List[Dict] = []
        for idx, similarity in semantic_matches:
            if 0 <= idx < len(base):
                srow = base.iloc[idx]
                enhanced_suggestions.append({"discipline": srow["__discipline"], "code": srow["__code_str"], "label": srow["__text"], "score": similarity * 100.0, "method": "semantic"})

        if isinstance(llm_analysis, dict) and llm_analysis.get("enhanced", False):
            for term in llm_analysis.get("search_terms", []) or []:
                term_result = search_disease(term, siddha_df, unani_df, merged_df, 3, 70)
                for sugg in term_result.get("suggestions", []) or []:
                    s2 = sugg.copy()
                    s2["method"] = f"{llm_provider}_suggested"
                    enhanced_suggestions.append(s2)

        if "suggestions" in traditional_result:
            for sugg in traditional_result["suggestions"]:
                s2 = sugg.copy()
                s2["method"] = "fuzzy"
                enhanced_suggestions.append(s2)

        unique: Dict[str, Dict] = {}
        for s in enhanced_suggestions:
            key = f"{s['discipline']}_{s['code']}"
            if key not in unique or s.get("score", 0) > unique[key].get("score", 0):
                unique[key] = s

        final_suggestions = sorted(unique.values(), key=lambda x: x.get("score", 0), reverse=True)[:fuzzy_top_k]

        return {
            "error": "No exact match found, showing intelligent suggestions",
            "suggestions": final_suggestions,
            "entities": entities,
            "llm_insights": llm_analysis,
            "search_method": search_method
        }
    except Exception as e:
        traditional_result["nlp_error"] = str(e)
        return traditional_result

def search_with_ai_enhancement(
    disease_name: str,
    siddha_path: str = SIDDHA_PATH,
    unani_path: str = UNANI_PATH,
    merged_path: str = MERGED_PATH,
    fuzzy_top_k: int = 5,
    fuzzy_threshold: int = 85,
    llm_provider: Optional[str] = None, # <-- Changed
    ollama_model: str = OLLAMA_MODEL    # <-- Added
) -> Dict:
    """Convenience wrapper for calling from FastAPI or CLI."""
    try:
        siddha_df = read_excel_smart(siddha_path)
        unani_df  = read_excel_smart(unani_path)
        merged_df = prepare_merged(read_excel_smart(merged_path))
        if llm_provider:
            return intelligent_search_disease(
                disease_name, siddha_df, unani_df, merged_df,
                fuzzy_top_k=fuzzy_top_k, fuzzy_threshold=fuzzy_threshold,
                llm_provider=llm_provider, ollama_model=ollama_model
            )
        else:
            return search_disease(
                disease_name, siddha_df, unani_df, merged_df,
                fuzzy_top_k=fuzzy_top_k, fuzzy_threshold=fuzzy_threshold
            )
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

def cli() -> None:
    ap = argparse.ArgumentParser(description="AYUSH disease code lookup with optional LLM enhancement")
    ap.add_argument("--siddha", default=SIDDHA_PATH, help="Path to Siddha .xls/.xlsx")
    ap.add_argument("--unani",  default=UNANI_PATH,  help="Path to Unani .xls/.xlsx")
    ap.add_argument("--merged", default=MERGED_PATH, help="Path to merged_dataset .xls/.xlsx")
    ap.add_argument("--threshold", type=int, default=85, help="Fuzzy threshold (0-100)")
    ap.add_argument("--topk", type=int, default=5, help="Suggestions count")
    ap.add_argument("--interactive", action="store_true", help="Interactive mode")
    ap.add_argument("--query", help="Single query")
    # --- New/changed LLM arguments ---
    ap.add_argument("--llm", choices=['openai', 'ollama'], help="Use a specific LLM for enhancement (e.g., 'openai', 'ollama')")
    ap.add_argument("--ollama-model", default=OLLAMA_MODEL, help=f"Ollama model to use (default: {OLLAMA_MODEL})")
    args = ap.parse_args()

    siddha_df = read_excel_smart(args.siddha)
    unani_df  = read_excel_smart(args.unani)
    merged_df = prepare_merged(read_excel_smart(args.merged))

    def run_once(q: str) -> None:
        res = search_with_ai_enhancement(
            q,
            siddha_path=args.siddha,
            unani_path=args.unani,
            merged_path=args.merged,
            fuzzy_top_k=args.topk,
            fuzzy_threshold=args.threshold,
            llm_provider=args.llm,
            ollama_model=args.ollama_model
        )
        print(json.dumps(res, ensure_ascii=False, indent=2))

    if args.query:
        run_once(args.query)
        return

    if args.interactive:
        print("--- AYUSH Disease Code Lookup ---")
        llm_status = "Disabled"
        if args.llm == 'openai' and openai_client:
            llm_status = "OpenAI (gpt-4o-mini)"
        elif args.llm == 'ollama' and ollama_client:
            llm_status = f"Ollama ({args.ollama_model})"
        elif args.llm:
            llm_status = f"{args.llm.capitalize()} (Requested but not available)"

        print(f"LLM Enhancement: {llm_status}")
        print("Datasets loaded.")
        while True:
            q = input("\nEnter disease name (or 'exit'): ").strip()
            if q.lower() in ("exit", "quit"):
                break
            if not q:
                continue
            run_once(q)
    else:
        ap.print_help()

if __name__ == "__main__":
    cli()