from sqlalchemy import Column, Integer, String, Text
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
