from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_, Integer
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

# Import database components
from database import get_db, engine, Base
import models

# Import ベクトルサーチ（更新版）
from components.search_researchers import (
    search_researchers, 
    search_researchers_pattern_a,
    search_researchers_pattern_b, 
    search_researchers_pattern_c,
    compare_all_patterns
)

# Load environment variables
load_dotenv()

# Create the FastAPI app with a title
app = FastAPI(
    title="KenQ Industry-Academia Collaboration API",
    description="API for managing researchers and projects with corrected pattern comparison",
    version="0.2.1"
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

# リクエストモデル
class SearchRequest(BaseModel):
    category: str
    title: str
    description: str
    university: str = "東京科学大学"
    top_k: int = 10

# パターン指定検索リクエストモデル
class PatternSearchRequest(BaseModel):
    category: str
    title: str
    description: str
    university: str = "東京科学大学"
    top_k: int = 10
    pattern: str  # "A", "B", "C"

# 単一研究者レスポンスモデル
class ResearcherResponse(BaseModel):
    researcher_id: str
    name: Optional[str] = ""
    university: str
    affiliation: str
    position: str
    research_field: Optional[str] = ""
    keywords: str
    explanation: str
    score: float
    pattern: Optional[str] = None

# パターン結果レスポンスモデル
class PatternResultResponse(BaseModel):
    results: List[ResearcherResponse]
    search_time: float
    pattern: str
    pattern_description: str

# 比較結果レスポンスモデル
class ComparisonResultResponse(BaseModel):
    pattern_a: PatternResultResponse
    pattern_b: PatternResultResponse
    pattern_c: PatternResultResponse
    total_comparison_time: float
    query_info: Dict[str, Any]

@app.get("/", tags=["General"])
def read_root():
    return {
        "Hello": "World", 
        "version": "0.2.1", 
        "status": "Field names corrected for Azure Search index",
        "new_features": ["Pattern Comparison", "Corrected Field Mapping"]
    }

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

# 既存の検索エンドポイント（後方互換性）
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

# パターン指定検索エンドポイント
@app.post("/search-researchers-pattern", response_model=PatternResultResponse, tags=["Researchers"])
def search_researchers_pattern_api(request: PatternSearchRequest):
    """
    指定されたパターンで研究者を検索
    pattern: "A", "B", "C"
    """
    try:
        if request.pattern.upper() == "A":
            result = search_researchers_pattern_a(
                category=request.category,
                title=request.title,
                description=request.description,
                university=request.university,
                top_k=request.top_k
            )
        elif request.pattern.upper() == "B":
            result = search_researchers_pattern_b(
                category=request.category,
                title=request.title,
                description=request.description,
                university=request.university,
                top_k=request.top_k
            )
        elif request.pattern.upper() == "C":
            result = search_researchers_pattern_c(
                category=request.category,
                title=request.title,
                description=request.description,
                university=request.university,
                top_k=request.top_k
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid pattern. Must be A, B, or C")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# パターン比較エンドポイント（新機能）
@app.post("/compare-patterns", response_model=ComparisonResultResponse, tags=["Researchers"])
def compare_patterns_api(request: SearchRequest):
    """
    3つのパターンすべてで研究者を検索し、結果を比較
    Pattern A: 研究者キーワードのみ（KAKEN）
    Pattern B: 研究者キーワード + 研究課題（KAKEN拡張）
    Pattern C: 研究者キーワード + 論文（KAKEN + researchmap）
    """
    try:
        comparison_results = compare_all_patterns(
            category=request.category,
            title=request.title,
            description=request.description,
            university=request.university,
            top_k=request.top_k
        )
        
        return comparison_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# パターン情報取得エンドポイント
@app.get("/patterns-info", tags=["Researchers"])
def get_patterns_info():
    """
    各パターンの詳細情報を取得
    """
    return {
        "patterns": {
            "A": {
                "name": "Pattern A",
                "description": "研究者キーワードのみ",
                "data_source": "KAKEN",
                "available_fields": ["researcher_id", "affiliation", "position", "keywords"],
                "features": [
                    "高速検索",
                    "基本的なマッチング",
                    "シンプルな検索アルゴリズム"
                ]
            },
            "B": {
                "name": "Pattern B", 
                "description": "研究者キーワード + 研究課題",
                "data_source": "KAKEN拡張",
                "available_fields": ["researcher_id", "affiliation", "position", "keywords", "research_projects"],
                "features": [
                    "研究課題を含む詳細マッチング",
                    "より精密な関連性評価",
                    "中程度の検索精度"
                ]
            },
            "C": {
                "name": "Pattern C",
                "description": "研究者キーワード + 論文（タイトル・概要）", 
                "data_source": "KAKEN + researchmap",
                "available_fields": ["researcher_id", "affiliation", "position", "keywords", "publications"],
                "features": [
                    "最高精度",
                    "論文情報を含む包括的マッチング",
                    "最も詳細な関連性分析"
                ]
            }
        },
        "comparison_benefits": [
            "精度の違いを比較分析",
            "検索時間の比較",
            "マッチング品質の違いを確認",
            "用途に応じた最適パターン選択"
        ]
    }

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

# --- Project matting endpoints ---
# 予算フィルター範囲マップ
budget_ranges = {
    "50万円〜": 0,
    "100万円〜": 1000000,
    "250万円〜": 2500000,
    "500万円〜": 5000000,
    "750万円〜": 7500000,
    "1000万円以上": 10000000,
    "設定なし": None
}

# 締切フィルター範囲マップ（日数）
deadline_ranges = {
    "7日以内": 7,
    "14日以内": 14,
    "30日以内": 30,
    "60日以内": 60,
    "90日以内": 90,
    "期限なし": None
}

@app.get("/matting-projects", tags=["Projects"])
def search_projects(
    keyword: str = "",
    budget_range: str = Query(None),
    deadline_range: str = Query(None),
    db: Session = Depends(get_db)
):
    try:
        keyword_pattern = f"%{keyword}%"
        filters = [
            or_(
                models.Project.project_title.ilike(keyword_pattern),
                models.Project.project_content.ilike(keyword_pattern),
                models.Project.research_field.ilike(keyword_pattern)
            )
        ]

        # 予算フィルター（文字列 → 数値比較用に前処理）
        if budget_range and budget_range in budget_ranges:
            min_yen = budget_ranges[budget_range]
            if min_yen is not None:
                filters.append(
                    and_(
                        models.Project.budget != None,
                        models.Project.budget != "",
                        models.Project.budget.cast(Integer) >= min_yen
                    )
                )

        # 締切フィルター（今日との差で計算）
        if deadline_range in deadline_ranges and deadline_ranges[deadline_range] is not None:
            deadline_date = datetime.now() + timedelta(days=deadline_ranges[deadline_range])
            filters.append(models.Project.application_deadline <= deadline_date.strftime("%Y-%m-%d %H:%M:%S"))

        results = (
            db.query(models.Project, models.Company)
            .join(models.CompanyUser, models.Project.company_user_id == models.CompanyUser.company_user_id)
            .join(models.Company, models.CompanyUser.company_id == models.Company.company_id)
            .filter(*filters)
            .limit(10)
            .all()
        )

        project_list = []
        for project, company in results:
            project_list.append({
                "project_id": project.project_id,
                "project_title": project.project_title,
                "project_content": project.project_content,
                "research_field": project.research_field,
                "project_status": project.project_status,
                "budget": project.budget,
                "preferred_researcher_level": project.preferred_researcher_level,
                "application_deadline": project.application_deadline,
                "company_name": company.company_name
            })

        return {
            "status": "success",
            "projects": project_list,
            "total": len(project_list)
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}