from sqlalchemy import Column, Integer, String, Text
from database import Base

class Researcher(Base):
    __tablename__ = "researcher_information"

    researcher_id = Column(String(8), primary_key=True)
    researcher_name = Column(String(255))
    name_kana = Column(String(255))
    name_alphabet = Column(String(255))
    university_research_institution = Column(String(255))
    affiliation = Column(String(255))
    position = Column(String(255))
    kaken_url = Column(String(45))
    email_address = Column(String(255))
    password = Column(String(255))
    research_field = Column(Text)
    keywords = Column(Text)
    research_project_counts = Column(Integer)
    output_counts = Column(Integer)

# New Project model - add this to your existing models.py
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