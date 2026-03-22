# main.py (or your FastAPI entrypoint)

from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime
import os
import json
import asyncio

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Search utilities from s.py (enhanced with AI)
from s import (
    search_disease,
    read_excel_smart,
    prepare_merged,
    intelligent_search_disease,
    search_with_ai_enhancement,
    NLP_AVAILABLE
)

# Import chatbot if available
try:
    from chatbot import AYUSHChatbot
    chatbot = AYUSHChatbot()
    CHATBOT_AVAILABLE = True
except ImportError:
    CHATBOT_AVAILABLE = False
    chatbot = None

# DB helpers
from db import init_db, get_db, LookupLog

# Dataset paths
SIDDHA_PATH = Path(r"C:\Users\ayush\Downloads\NATIONAL SIDDHA MORBIDITY CODES.xls")
UNANI_PATH  = Path(r"C:\Users\ayush\Downloads\NATIONAL UNANI MORBIDITY CODES.xls")
MERGED_PATH = Path(r"C:\Users\ayush\Downloads\merged_dataset.xlsx")

# Load datasets at startup with caching
print("Loading AYUSH datasets...")
try:
    siddha_df = read_excel_smart(SIDDHA_PATH)
    unani_df  = read_excel_smart(UNANI_PATH)
    merged_df = prepare_merged(read_excel_smart(MERGED_PATH))
    print(f"✅ Datasets loaded: Siddha ({len(siddha_df)}), Unani ({len(unani_df)}), Merged ({len(merged_df)})")
except Exception as e:
    print(f"❌ Error loading datasets: {e}")
    siddha_df = unani_df = merged_df = None

# FastAPI app with enhanced metadata
app = FastAPI(
    title="AYUSH Intelligent Lookup API",
    description="AI-powered traditional medicine lookup system with Siddha, Unani, and Ayurveda integration",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enhanced CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:8000", "http://127.0.0.1:8000",
        "http://localhost", "http://127.0.0.1",
        "http://localhost:5173", "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Assume all HTML files are in a "templates" directory
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def on_startup():
    """Initialize database and perform startup checks"""
    init_db()
    print(f"🤖 NLP/LLM Available: {NLP_AVAILABLE}")
    print(f"💬 Chatbot Available: {CHATBOT_AVAILABLE}")
    print(f"🌿 AYUSH Lookup API started successfully!")

# ========================================
# PYDANTIC MODELS
# ========================================

class LookupRequest(BaseModel):
    patient_id: Optional[str] = None
    disease_text: str
    fuzzy_threshold: int = 85
    fuzzy_top_k: int = 5
    use_ai: Optional[bool] = True

    @field_validator('disease_text')
    @classmethod
    def validate_disease_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('disease_text cannot be empty')
        return v

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    patient_id: Optional[str] = None

class IntelligentLookupRequest(BaseModel):
    patient_id: Optional[str] = None
    natural_language_query: str
    patient_profile: Optional[Dict] = None
    fuzzy_top_k: int = 5
    fuzzy_threshold: int = 85

class LookupResponse(BaseModel):
    patient_id: Optional[str] = None
    result: Dict
    timestamp: str
    ai_enhanced: bool = False
    search_method: str = "traditional"

class ChatResponse(BaseModel):
    response: str
    timestamp: str
    conversation_id: Optional[str] = None

# ========================================
# FRONTEND ROUTES
# ========================================

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    """Serves the main search page, which handles auth redirect."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse) 
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/login.html", response_class=HTMLResponse)
def login_html(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/index.html", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/result.html", response_class=HTMLResponse)
def result_html(request: Request):
    return templates.TemplateResponse("result.html", {"request": request})

@app.get("/shop.html", response_class=HTMLResponse)
def shop_html(request: Request):
    return templates.TemplateResponse("shop.html", {"request": request})
    
@app.get("/chatbot.html", response_class=HTMLResponse)
def chatbot_html(request: Request):
    return templates.TemplateResponse("chatbot.html", {
        "request": request,
        "chatbot_available": CHATBOT_AVAILABLE
    })

@app.get("/clinic.html", response_class=HTMLResponse)
def clinic_html(request: Request):
    return templates.TemplateResponse("clinic.html", {"request": request})

@app.get("/clinic-login", response_class=HTMLResponse)
def clinic_login_page(request: Request):
    """Provides an endpoint for the clinic login link."""
    return templates.TemplateResponse("clinic.html", {"request": request})

@app.get("/clinicdashboard.html", response_class=HTMLResponse)
def clinic_dashboard_html(request: Request):
    return templates.TemplateResponse("clinicdashboard.html", {"request": request})

# ========================================
# API INFORMATION ROUTES
# ========================================

@app.get("/status")
def status():
    """System status endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "datasets_loaded": siddha_df is not None and unani_df is not None and merged_df is not None,
        "nlp_available": NLP_AVAILABLE,
        "chatbot_available": CHATBOT_AVAILABLE,
        "version": "2.0.0"
    }

@app.get("/api/capabilities")
def get_capabilities():
    """Get system capabilities"""
    return {
        "traditional_search": True,
        "fuzzy_matching": True,
        "semantic_search": NLP_AVAILABLE,
        "llm_enhancement": NLP_AVAILABLE,
        "conversational_ai": CHATBOT_AVAILABLE,
        "supported_systems": ["Siddha", "Unani", "Ayurveda"],
        "languages": ["English"],
        "features": [
            "Exact matching",
            "Partial matching", 
            "Fuzzy search",
            "Semantic similarity" if NLP_AVAILABLE else None,
            "Natural language processing" if NLP_AVAILABLE else None,
            "AI chat assistant" if CHATBOT_AVAILABLE else None
        ]
    }

# ========================================
# CORE API ROUTES
# ========================================

@app.post("/lookup", response_model=LookupResponse)
async def lookup(req: LookupRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Enhanced lookup with optional AI integration"""
    if siddha_df is None or unani_df is None or merged_df is None:
        raise HTTPException(status_code=500, detail="Datasets not loaded")
    
    text = req.disease_text.strip()
    timestamp = datetime.now().isoformat()
    
    try:
        if req.use_ai and NLP_AVAILABLE:
            result = await asyncio.to_thread(
                intelligent_search_disease,
                disease_name=text,
                siddha_df=siddha_df,
                unani_df=unani_df,
                merged_df=merged_df,
                fuzzy_top_k=req.fuzzy_top_k,
                fuzzy_threshold=req.fuzzy_threshold,
                use_llm=True
            )
            search_method = "ai_enhanced"
            ai_enhanced = True
        else:
            result = await asyncio.to_thread(
                search_disease,
                text,
                siddha_df=siddha_df,
                unani_df=unani_df,
                merged_df=merged_df,
                fuzzy_top_k=req.fuzzy_top_k,
                fuzzy_threshold=req.fuzzy_threshold,
            )
            search_method = "traditional"
            ai_enhanced = False
        
        background_tasks.add_task(
            log_lookup,
            db=db,
            patient_id=req.patient_id,
            disease_text=text,
            result=result,
            search_method=search_method
        )
        
        return LookupResponse(
            patient_id=req.patient_id,
            result=result,
            timestamp=timestamp,
            ai_enhanced=ai_enhanced,
            search_method=search_method
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/intelligent-lookup")
async def intelligent_lookup(req: IntelligentLookupRequest, db: Session = Depends(get_db)):
    """Advanced natural language lookup with AI"""
    if not NLP_AVAILABLE:
        raise HTTPException(status_code=501, detail="AI features not available.")
    
    if siddha_df is None or unani_df is None or merged_df is None:
        raise HTTPException(status_code=500, detail="Datasets not loaded")
    
    try:
        result = await asyncio.to_thread(
            intelligent_search_disease,
            disease_name=req.natural_language_query,
            siddha_df=siddha_df,
            unani_df=unani_df,
            merged_df=merged_df,
            fuzzy_top_k=req.fuzzy_top_k,
            fuzzy_threshold=req.fuzzy_threshold,
            use_llm=True
        )
        
        if req.patient_profile and chatbot:
            try:
                profile_analysis = await asyncio.to_thread(
                    chatbot.analyze_symptoms_and_suggest_codes,
                    f"{req.natural_language_query} Patient: {req.patient_profile}"
                )
                result["patient_analysis"] = profile_analysis
            except Exception:
                pass
        
        return {
            "result": result,
            "patient_id": req.patient_id,
            "timestamp": datetime.now().isoformat(),
            "search_type": "intelligent",
            "query": req.natural_language_query
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intelligent lookup failed: {str(e)}")

# --- SSE streaming helpers and endpoint ---

def sse_chat_generator(message: str):
    """
    Synchronous generator that yields SSE-framed chunks.
    Each event must end with a blank line per SSE spec.
    """
    try:
        for chunk in chatbot.chat_stream(message):  # generator yields text chunks
            data = json.dumps({"delta": chunk})
            # SSE frame: 'data: ...\n\n'
            yield f"data: {data}\n\n"
    except Exception as e:
        err = json.dumps({"error": str(e)})
        yield f"event: error\ndata: {err}\n\n"

@app.post("/chat")
async def chat_with_ayush(req: ChatRequest):
    """Chat with AYUSH AI assistant using SSE streaming."""
    if not CHATBOT_AVAILABLE or not hasattr(chatbot, 'chat_stream'):
        raise HTTPException(status_code=501, detail="Streaming chatbot not available.")
    return StreamingResponse(
        sse_chat_generator(req.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # "X-Accel-Buffering": "no",  # uncomment for Nginx if buffering issues
        },
    )

# ========================================
# BACKGROUND TASKS & ERROR HANDLERS
# ========================================

def log_lookup(db: Session, patient_id: Optional[str], disease_text: str, result: Dict, search_method: str):
    """Background task to log searches"""
    try:
        log_entry = LookupLog(
            patient_id=patient_id,
            disease_text=disease_text,
            result_json={**result, "search_method": search_method}
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to log lookup: {e}")

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

# ========================================
# HEALTH CHECK
# ========================================

@app.get("/health")
def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "database": "healthy",
            "datasets": "healthy" if siddha_df is not None else "unhealthy",
            "nlp_engine": "healthy" if NLP_AVAILABLE else "unavailable",
            "chatbot": "healthy" if CHATBOT_AVAILABLE else "unavailable"
        },
        "metrics": {
            "siddha_records": len(siddha_df) if siddha_df is not None else 0,
            "unani_records": len(unani_df) if unani_df is not None else 0,
            "merged_records": len(merged_df) if merged_df is not None else 0
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
