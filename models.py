from sqlalchemy import Column, Integer, String, Text
from database import Base

class Researcher(Base):
    __tablename__ = "researcher_information"

    # Based on your database schema image, the actual column names are:
    researcher_id = Column(String(8), primary_key=True)
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
    other_urls = Column(String(500))

# Add the missing models that are referenced in main.py
class ResearchProject(Base):
    __tablename__ = "research_projects"  # Update this to match your actual table name
    
    id = Column(Integer, primary_key=True)
    research_project_id = Column(String(255))
    researcher_id = Column(String(8))  # Changed to String to match Researcher
    research_project_title = Column(String(255))
    research_project_details = Column(Text)
    research_field = Column(String(255))
    research_achievement = Column(Text)

class Company(Base):
    __tablename__ = "companies"  # Update this to match your actual table name
    
    company_id = Column(Integer, primary_key=True)
    company_name = Column(String(255))

class CompanyUser(Base):
    __tablename__ = "company_users"  # Update this to match your actual table name
    
    company_user_id = Column(Integer, primary_key=True)
    company_id = Column(Integer)

class Project(Base):
    __tablename__ = "project_information"

    project_id = Column(Integer, primary_key=True)
    types_to_register = Column(String(255))
    company_user_id = Column(Integer)
    project_title = Column(String(255))
    consultation_category = Column(Integer)
    project_content = Column(Text)
    research_field = Column(String(255))
    preferred_researcher_level = Column(String(255))
    budget = Column(String(255))
    application_deadline = Column(String(255))
    project_status = Column(Integer)
    closed_date = Column(String(255))