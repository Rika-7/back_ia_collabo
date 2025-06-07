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
    title="KenQ Industry-Academia Collaboration API",
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

# Research Project response model
class ResearchProjectResponse(BaseModel):
    id: int
    research_project_id: str
    researcher_id: int
    research_project_title: str
    research_project_details: str
    research_field: str
    research_achievement: Optional[str] = None

# Research Project search request model
class ResearchProjectSearchRequest(BaseModel):
    keyword: Optional[str] = None
    research_field: Optional[str] = None
    researcher_id: Optional[int] = None


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
                "name_kana": r.researcher_name_kana,
                "name_alphabet": r.researcher_name_alphabet,
                "affiliation": r.researcher_affiliation_current,
                "department": r.researcher_department_current,
                "position": r.researcher_position_current,
                "email": r.researcher_email,
                "research_field": r.research_field_pi,
                "keywords": r.keywords_pi
            })
        
        return {"status": "success", "researchers": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/researchers/{researcher_id}", tags=["Researchers"])
def get_researcher_by_id(researcher_id: int, db: Session = Depends(get_db)):
    try:
        # Find researcher by ID
        researcher = db.query(models.Researcher).filter(models.Researcher.researcher_id == researcher_id).first()
        
        if not researcher:
            return {"status": "error", "message": "Researcher not found"}
            
        # Convert to dictionary
        result = {
            "id": researcher.researcher_id,
            "name": researcher.researcher_name,
            "name_kana": researcher.researcher_name_kana,
            "name_alphabet": researcher.researcher_name_alphabet,
            "affiliation_current": researcher.researcher_affiliation_current,
            "department_current": researcher.researcher_department_current,
            "position_current": researcher.researcher_position_current,
            "affiliations_past": researcher.researcher_affiliations_past,
            "kaken_url": researcher.kaken_url,
            "email": researcher.researcher_email,
            "research_field": researcher.research_field_pi,
            "keywords": researcher.keywords_pi,
            "researchmap_url": researcher.researchmap_url,
            "jglobal_url": researcher.jglobal_url,
            "orcid_url": researcher.orcid_url,
            "other_urls": researcher.other_urls
        }
        
        return {"status": "success", "researcher": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# リクエストモデル
class SearchRequest(BaseModel):
    category: str
    title: str
    description: str
    university: str = "東京科学大学"
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

# --- Research Project endpoints ---
@app.get("/research-projects", tags=["Research Projects"])
def get_research_projects(page: int = 1, per_page: int = 10, db: Session = Depends(get_db)):
    try:
        # Calculate offset for pagination
        offset = (page - 1) * per_page
        
        # Get research projects
        projects = db.query(models.ResearchProject).offset(offset).limit(per_page).all()
        
        # Get total count
        total = db.query(models.ResearchProject).count()
        
        # Convert to list of dictionaries
        result = []
        for p in projects:
            result.append({
                "id": p.id,
                "research_project_id": p.research_project_id,
                "researcher_id": p.researcher_id,
                "research_project_title": p.research_project_title,
                "research_field": p.research_field
            })
        
        return {
            "status": "success",
            "research_projects": result,
            "total": total,
            "page": page,
            "per_page": per_page
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/research-projects/{project_id}", tags=["Research Projects"])
def get_research_project_by_id(project_id: int, db: Session = Depends(get_db)):
    try:
        # Find research project by ID
        project = db.query(models.ResearchProject).filter(models.ResearchProject.id == project_id).first()
        
        if not project:
            return {"status": "error", "message": "Research project not found"}
        
        # Convert to dictionary
        result = {
            "id": project.id,
            "research_project_id": project.research_project_id,
            "researcher_id": project.researcher_id,
            "research_project_title": project.research_project_title,
            "research_project_details": project.research_project_details,
            "research_field": project.research_field,
            "research_achievement": project.research_achievement
        }
        
        return {"status": "success", "research_project": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/search-research-projects", tags=["Research Projects"])
def search_research_projects(keyword: str = "", db: Session = Depends(get_db)):
    try:
        # Search in title, details, and research field
        projects = db.query(models.ResearchProject).filter(
            or_(
                models.ResearchProject.research_project_title.contains(keyword),
                models.ResearchProject.research_project_details.contains(keyword),
                models.ResearchProject.research_field.contains(keyword)
            )
        ).limit(10).all()
        
        # Convert to list of dictionaries
        result = []
        for p in projects:
            result.append({
                "id": p.id,
                "research_project_id": p.research_project_id,
                "researcher_id": p.researcher_id,
                "research_project_title": p.research_project_title,
                "research_field": p.research_field
            })
        
        return {
            "status": "success",
            "research_projects": result,
            "total": len(result)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@app.get("/filtered-research-projects", tags=["Research Projects"])
def get_filtered_research_projects(
    research_field: str = Query(None), 
    researcher_id: int = Query(None),
    limit: int = 6,
    db: Session = Depends(get_db)
):
    try:
        # Build the query with filters
        query = db.query(models.ResearchProject)
        
        # Add filter conditions if provided
        if research_field:
            query = query.filter(models.ResearchProject.research_field.contains(research_field))
        
        if researcher_id:
            query = query.filter(models.ResearchProject.researcher_id == researcher_id)
        
        # Get research projects with limit
        projects = query.limit(limit).all()
        
        # Convert to list of dictionaries
        result = []
        for p in projects:
            result.append({
                "id": p.id,
                "research_project_id": p.research_project_id,
                "researcher_id": p.researcher_id,
                "research_project_title": p.research_project_title,
                "research_field": p.research_field,
                "research_achievement": p.research_achievement
            })
        
        return {
            "status": "success",
            "research_projects": result,
            "total": len(result)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- Get research projects by researcher ID ---
@app.get("/researchers/{researcher_id}/research-projects", tags=["Researchers"])
def get_research_projects_by_researcher(researcher_id: int, db: Session = Depends(get_db)):
    try:
        # Get all research projects for a specific researcher
        projects = db.query(models.ResearchProject).filter(
            models.ResearchProject.researcher_id == researcher_id
        ).all()
        
        # Convert to list of dictionaries
        result = []
        for p in projects:
            result.append({
                "id": p.id,
                "research_project_id": p.research_project_id,
                "research_project_title": p.research_project_title,
                "research_project_details": p.research_project_details,
                "research_field": p.research_field,
                "research_achievement": p.research_achievement
            })
        
        return {
            "status": "success",
            "research_projects": result,
            "total": len(result)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}