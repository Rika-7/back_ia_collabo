from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List

# Import database components
from database import get_db, engine, Base
import models

# Import ベクトルサーチ
from components.search_researchers import search_researchers

# Load environment variables
load_dotenv()

app = FastAPI()

# ミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables (uncomment when you have models defined)
# Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/test-db")
def test_database(db: Session = Depends(get_db)):
    try:
        # Execute a simple query with proper text() wrapper
        result = db.execute(text("SELECT 1")).fetchone()
        return {"status": "success", "result": str(result[0])}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/researchers")
def get_researchers(db: Session = Depends(get_db)):
    try:
        # Get the first 10 researchers
        researchers = db.query(models.Researcher).limit(10).all()
        
        # Convert to a list of dictionaries
        result = []
        for r in researchers:
            result.append({
                "id": r.researcher_id,
                "name": r.researcher_name,
                "affiliation": r.affiliation,
                "position": r.position,
                "email": r.email_address,
                "field": r.research_field
            })
        
        return {"status": "success", "researchers": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/researchers/{researcher_id}")
def get_researcher_by_id(researcher_id: str, db: Session = Depends(get_db)):
    try:
        # Find researcher by ID
        researcher = db.query(models.Researcher).filter(models.Researcher.researcher_id == researcher_id).first()
        
        if not researcher:
            return {"status": "error", "message": "Researcher not found"}
            
        # Convert to dictionary
        result = {
            "id": researcher.researcher_id,
            "name": researcher.researcher_name,
            "name_kana": researcher.name_kana,
            "name_alphabet": researcher.name_alphabet,
            "university": researcher.university_research_institution,
            "affiliation": researcher.affiliation,
            "position": researcher.position,
            "kaken_url": researcher.kaken_url,
            "email": researcher.email_address,
            "research_field": researcher.research_field,
            "keywords": researcher.keywords,
            "research_project_counts": researcher.research_project_counts,
            "output_counts": researcher.output_counts
        }
        
        return {"status": "success", "researcher": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}



# リクエストモデル
class SearchRequest(BaseModel):
    category: str
    title: str
    description: str
    university:str = "東京科学大学"
    top_k: int = 10  # 10件取得

# レスポンスモデル
class ResearcherResponse(BaseModel):
    researcher_id: str
    name: str
    university: str
    affiliation: str
    position: str
    research_field: str
    keywords: str
    explanation: str
    score: float

@app.post("/search-researchers",response_model=List[ResearcherResponse])
def search_researchers_api(request: SearchRequest):
    try:
        search_results = search_researchers(
            category=request.category,
            title=request.title,
            description=request.description,
            university=request.university,
            top_k=request.top_k
            )
        
        return search_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))