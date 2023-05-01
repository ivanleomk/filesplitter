# coding: utf-8
from sqlalchemy import Column, Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.mysql import DATETIME, MEDIUMINT, TINYINT
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class Company(Base):
    __tablename__ = 'Company'

    id = Column(Integer, primary_key=True)
    company_name = Column(String(1000, 'utf8mb4_unicode_ci'), nullable=False)
    user_id = Column(String(500, 'utf8mb4_unicode_ci'), nullable=False)


class Customer(Base):
    __tablename__ = 'Customer'

    customer_id = Column(Integer, primary_key=True)
    user_id = Column(String(500, 'utf8mb4_unicode_ci'), nullable=False)
    company_id = Column(Integer, nullable=False)
    biodata = Column(String(1000, 'utf8mb4_unicode_ci'), nullable=False)
    title = Column(String(1000, 'utf8mb4_unicode_ci'), nullable=False)


class Deal(Base):
    __tablename__ = 'Deal'

    deal_id = Column(Integer, primary_key=True)
    deal_size = Column(MEDIUMINT, nullable=False)
    deal_description = Column(String(10000, 'utf8mb4_unicode_ci'), nullable=False)
    customer_id = Column(Integer, nullable=False)


class Email(Base):
    __tablename__ = 'Email'

    email_id = Column(Integer, primary_key=True)
    email_content = Column(String(10000, 'utf8mb4_unicode_ci'), nullable=False)
    prospects_involved = Column(String(1000, 'utf8mb4_unicode_ci'), nullable=False)


class File(Base):
    __tablename__ = 'File'

    id = Column(Integer, primary_key=True)
    key = Column(String(191, 'utf8mb4_unicode_ci'), nullable=False, unique=True)
    url = Column(String(1000, 'utf8mb4_unicode_ci'), nullable=False)
    createdAt = Column(DATETIME(fsp=3), nullable=False, server_default=text("CURRENT_TIMESTAMP(3)"))
    isProcessing = Column(TINYINT(1), nullable=False, server_default=text("'0'"))
    startedprocessing = Column(DATETIME(fsp=3), nullable=False, server_default=text("CURRENT_TIMESTAMP(3)"))
    isTranscribed = Column(TINYINT(1), nullable=False, server_default=text("'0'"))
    transcript = Column(String(10000, 'utf8mb4_unicode_ci'))


class Meeting(Base):
    __tablename__ = 'Meeting'

    meeting_id = Column(Integer, primary_key=True)
    user_id = Column(String(500, 'utf8mb4_unicode_ci'), nullable=False)
    summary = Column(String(1000, 'utf8mb4_unicode_ci'), nullable=False)
    meeting_date = Column(TIMESTAMP, nullable=False)
    meeting_notes = Column(String(1000, 'utf8mb4_unicode_ci'), nullable=False)


class Note(Base):
    __tablename__ = 'Note'

    note_id = Column(Integer, primary_key=True)
    note_text = Column(String(10000, 'utf8mb4_unicode_ci'), nullable=False)


class User(Base):
    __tablename__ = 'User'

    user_id = Column(String(500, 'utf8mb4_unicode_ci'), primary_key=True, unique=True)
    user_name = Column(String(1000, 'utf8mb4_unicode_ci'), nullable=False)
    credits = Column(MEDIUMINT, nullable=False, server_default=text("'0'"))


class Waitlist(Base):
    __tablename__ = 'Waitlist'

    email = Column(String(200, 'utf8mb4_unicode_ci'), primary_key=True, unique=True)
    goal = Column(String(191, 'utf8mb4_unicode_ci'), nullable=False, server_default=text("'Sales'"))
    name = Column(String(1000, 'utf8mb4_unicode_ci'), nullable=False)
    createAt = Column(DATETIME(fsp=3), nullable=False, server_default=text("CURRENT_TIMESTAMP(3)"))


class Collateral(Base):
    __tablename__ = 'collateral'

    collateral_id = Column(Integer, primary_key=True)
    url = Column(String(1000, 'utf8mb4_unicode_ci'), nullable=False)
    summary = Column(String(1000, 'utf8mb4_unicode_ci'), nullable=False)
