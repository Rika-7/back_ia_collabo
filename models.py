from sqlalchemy import Column, Integer, String, Text
from database import Base

# Simple model for the researcher_information table
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