from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship
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
    company_user_id = Column(Integer, ForeignKey('company_user.company_user_id'))
    project_title = Column(String(255))
    consultation_category = Column(Integer)
    project_content = Column(Text)
    research_field = Column(String(255))
    preferred_researcher_level = Column(String(255))
    budget = Column(String(255))
    application_deadline = Column(String(255))
    project_status = Column(Integer)
    closed_date = Column(String(255))

    user = relationship("CompanyUser", back_populates="projects")


class Company(Base):
    __tablename__="company"

    company_id = Column(Integer,primary_key=True)
    company_name = Column(String(255))
    company_plan = Column(String(255))

    users = relationship("CompanyUser", back_populates="company")


class CompanyUser(Base):
    __tablename__="company_user"

    company_user_id = Column(Integer,primary_key=True)
    company_id = Column(Integer, ForeignKey('company.company_id'))
    company_user_name = Column(String(255))
    department = Column(String(255))
    company_user_email = Column(String(255))
    password = Column(String(255))

    company = relationship("Company", back_populates="users")
    projects = relationship("Project", back_populates="user")