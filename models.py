from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base

class Researcher(Base):
    __tablename__ = "researcher_information"

    researcher_id = Column(Integer, primary_key=True)
    researcher_name = Column(String(255))
    researcher_name_kana = Column(String(255))
    researcher_name_alphabet = Column(String(255))
    researcher_affiliation_current = Column(String(500))
    researcher_department_current = Column(String(500))
    researcher_position_current = Column(String(255))
    researcher_affiliations_past = Column(String(1000))
    research_field_pi = Column(String(1000))
    keywords_pi = Column(Text)
    kaken_url = Column(String(500))
    researcher_email = Column(String(255))
    researcher_password = Column(String(255))
    researchmap_url = Column(String(500))
    jglobal_url = Column(String(500))
    orcid_url = Column(String(500))
    other_urls = Column(Text)

class ResearchProject(Base):
    __tablename__ = "research_project"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    research_project_id = Column(String(255))
    researcher_id = Column(Integer)
    research_project_title = Column(String(1000))
    research_project_details = Column(Text)
    research_field = Column(String(500))
    research_achievement = Column(Text)

# Company related models for project matching
class Company(Base):
    __tablename__ = "company"
    
    company_id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(255), nullable=False)
    company_description = Column(Text)
    company_website = Column(String(500))
    company_address = Column(String(500))
    company_phone = Column(String(50))
    company_email = Column(String(255))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class CompanyUser(Base):
    __tablename__ = "company_user"
    
    company_user_id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("company.company_id"))
    user_name = Column(String(255))
    user_email = Column(String(255))
    user_password = Column(String(255))
    user_position = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    
    # Relationship
    company = relationship("Company", backref="users")

class Project(Base):
    __tablename__ = "project"
    
    project_id = Column(Integer, primary_key=True, autoincrement=True)
    company_user_id = Column(Integer, ForeignKey("company_user.company_user_id"))
    project_title = Column(String(500), nullable=False)
    project_content = Column(Text)
    research_field = Column(String(500))
    project_status = Column(String(100))  # "募集中", "進行中", "完了", etc.
    budget = Column(String(100))  # Store as string like "100万円"
    preferred_researcher_level = Column(String(255))  # "教授", "准教授", "助教", etc.
    application_deadline = Column(DateTime)
    project_start_date = Column(DateTime)
    project_end_date = Column(DateTime)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    
    # Relationship
    company_user = relationship("CompanyUser", backref="projects")