from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, or_
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Optional

# Import database components
from database import get_db, engine, Base
import models

# Import ベクトルサーチ
from components.search_researchers import search_researchers

# Load environment variables
load_dotenv()

# Create the FastAPI app with a title
app = FastAPI(
    title="Research API",
    description="API for managing researchers and projects",
    version="0.1.0"
)

# ミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project response model
class ProjectResponse(BaseModel):
    project_id: int
    types_to_register: str
    company_user_id: int
    project_title: str
    consultation_category: int
    project_content: str
    research_field: str
    preferred_researcher_level: str
    budget: str
    application_deadline: str
    project_status: int
    closed_date: Optional[str] = None

# Project search request model
class ProjectSearchRequest(BaseModel):
    keyword: Optional[str] = None
    category: Optional[int] = None
    status: Optional[int] = None


@app.get("/", tags=["General"])
def read_root():
    return {"Hello": "World"}

# --- Researcher endpoints ---
@app.get("/researchers", tags=["Researchers"])
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

@app.get("/researchers/{researcher_id}", tags=["Researchers"])
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

@app.post("/search-researchers", response_model=List[ResearcherResponse], tags=["Researchers"])
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

# --- Project endpoints ---
@app.get("/projects", tags=["Projects"])
def get_projects(page: int = 1, per_page: int = 10, db: Session = Depends(get_db)):
    try:
        # Calculate offset for pagination
        offset = (page - 1) * per_page
        
        # Get projects
        projects = db.query(models.Project).offset(offset).limit(per_page).all()
        
        # Get total count
        total = db.query(models.Project).count()
        
        # Convert to list of dictionaries
        result = []
        for p in projects:
            result.append({
                "project_id": p.project_id,
                "project_title": p.project_title,
                "research_field": p.research_field,
                "project_status": p.project_status
            })
        
        return {
            "status": "success",
            "projects": result,
            "total": total,
            "page": page,
            "per_page": per_page
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/projects/{project_id}", tags=["Projects"])
def get_project_by_id(project_id: int, db: Session = Depends(get_db)):
    try:
        # Find project by ID
        project = db.query(models.Project).filter(models.Project.project_id == project_id).first()
        
        if not project:
            return {"status": "error", "message": "Project not found"}
        
        # Convert to dictionary
        result = {
            "project_id": project.project_id,
            "types_to_register": project.types_to_register,
            "company_user_id": project.company_user_id,
            "project_title": project.project_title,
            "consultation_category": project.consultation_category,
            "project_content": project.project_content,
            "research_field": project.research_field,
            "preferred_researcher_level": project.preferred_researcher_level,
            "budget": project.budget,
            "application_deadline": project.application_deadline,
            "project_status": project.project_status,
            "closed_date": project.closed_date
        }
        
        return {"status": "success", "project": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/search-projects", tags=["Projects"])
def search_projects(keyword: str = "", db: Session = Depends(get_db)):
    try:
        # Search in title, content, and research field
        projects = db.query(models.Project).filter(
            or_(
                models.Project.project_title.contains(keyword),
                models.Project.project_content.contains(keyword),
                models.Project.research_field.contains(keyword)
            )
        ).limit(10).all()
        
        # Convert to list of dictionaries
        result = []
        for p in projects:
            result.append({
                "project_id": p.project_id,
                "project_title": p.project_title,
                "research_field": p.research_field,
                "project_status": p.project_status
            })
        
        return {
            "status": "success",
            "projects": result,
            "total": len(result)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
    # Add this endpoint to your main.py file

@app.get("/filtered-projects", tags=["Projects"])
def get_filtered_projects(
    types_to_register: str = Query(None), 
    preferred_researcher_level: str = Query(None),
    limit: int = 6,
    db: Session = Depends(get_db)
):
    try:
        # Build the query with filters
        query = db.query(models.Project)
        
        # Add filter conditions if provided
        if types_to_register:
            query = query.filter(models.Project.types_to_register == types_to_register)
        
        if preferred_researcher_level:
            query = query.filter(models.Project.preferred_researcher_level == preferred_researcher_level)
        
        # Get projects with limit
        projects = query.limit(limit).all()
        
        # Convert to list of dictionaries
        result = []
        for p in projects:
            result.append({
                "project_id": p.project_id,
                "project_title": p.project_title,
                "research_field": p.research_field,
                "budget": p.budget,
                "application_deadline": p.application_deadline,
                "preferred_researcher_level": p.preferred_researcher_level,
                "types_to_register": p.types_to_register,
                "project_status": p.project_status
            })
        
        return {
            "status": "success",
            "projects": result,
            "total": len(result)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}