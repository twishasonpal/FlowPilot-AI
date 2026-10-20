import os

class Config:
    SECRET_KEY=os.getenv("SECRET_KEY","local-dev-only-change-me")
    DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///flowpilot.db")
    GEMINI_MODEL=os.getenv("GEMINI_MODEL","gemini-2.0-flash")
    ENABLE_AI_PLANNING=os.getenv("ENABLE_AI_PLANNING","false").lower()=="true"
    ENABLE_SEMANTIC_SEARCH=False
    MAX_UPLOAD_BYTES=int(os.getenv("MAX_UPLOAD_BYTES","5000000"))
