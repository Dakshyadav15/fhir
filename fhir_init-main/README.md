# 🌿 AYUSH Intelligent Lookup API

An AI-powered traditional medicine lookup and health information system designed for integration with **Siddha, Unani, and Ayurveda** systems. This project leverages natural language processing and FHIR standards to provide intelligent medical code lookup and patient data management.

## 🚀 Overview

The AYUSH Intelligent Lookup API is a modern, high-performance backend built with **FastAPI** that serves as a bridge between traditional Indian medicine (AYUSH) and contemporary digital health standards (FHIR). It features AI-driven search capabilities, a conversational assistant, and seamless dataset integration.

## ✨ Key Features

- **🔍 Intelligent Lookup**: Multi-system disease and morbidity code lookup across Siddha, Unani, and Ayurveda datasets.
- **🧠 AI-Enhanced Search**: Utilizes natural language processing for fuzzy matching and semantic similarity to help practitioners find the right codes even with imprecise queries.
- **💬 AYUSH Chatbot**: A conversational AI assistant that can analyze symptoms and suggest relevant morbidity codes in real-time.
- **🏥 FHIR Integration**: Built-in support for HL7 FHIR standards for interoperable healthcare data exchange.
- **📊 Dataset Management**: Automated loading and processing of national morbidity code datasets (Excel/XLS formats).
- **📝 Auditing & Logging**: Comprehensive logging of all lookups and system activities for traceability.
- **💻 Modern Frontend**: Includes a React-based frontend (Vite) and responsive Jinja2-templated pages for various user roles.

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLAlchemy & SQLite
- **AI/NLP**: Custom NLP engine & LLM integration
- **Standards**: HL7 FHIR
- **Frontend**: React (Vite), Tailwind CSS (in frontend app), Jinja2 Templates (for server-rendered views)
- **Data Processing**: Pandas, Openpyxl

## 📂 Project Structure

```bash
├── app.py                  # Main FastAPI entry point
├── chatbot.py               # AI Chatbot logic and LLM integration
├── fhir_router.py           # FHIR-compliant API endpoints
├── fhir_service.py          # Business logic for FHIR services
├── fhir_models.py           # Data models for FHIR resources
├── db.py                    # Database configuration and models
├── s.py                     # Core search and NLP utilities
├── ayush-frontend/          # React frontend application (Vite)
├── templates/               # Jinja2 HTML templates
├── requirements.txt         # Python dependencies
└── .env                     # Environment variables (API keys, etc.)
```

## ⚙️ Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js & npm (for frontend)

### Backend Setup
1. Clone the repository.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables in `.env`:
   ```ini
   DATABASE_URL=sqlite:///./ayush_lookup.db
   # Add AI/LLM API keys if required
   ```
5. Run the server:
   ```bash
   python app.py
   ```
   The API will be available at `http://127.0.0.1:8000`. Documentation can be found at `/docs`.

### Frontend Setup (Vite)
1. Navigate to the frontend directory:
   ```bash
   cd ayush-frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```

## 📜 API Documentation

Once the server is running, you can access the interactive API documentation:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## 🤝 Contributing

Contributions to improve the AYUSH Intelligent Lookup API are welcome. Feel free to open issues or submit pull requests.

---
*Created for the National Health Mission and AYUSH systems integration.*
