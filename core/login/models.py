from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from core.login.database import Base
import datetime


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)


class TokenTable(Base):
    __tablename__ = "token"
    user_id = Column(Integer)
    access_toke = Column(String(450), primary_key=True)
    refresh_toke = Column(String(450), nullable=False)
    status = Column(Boolean)
    created_date = Column(DateTime, default=datetime.datetime.now)


class HisActivityTable(Base):
    __tablename__ = "history_activity"
    his_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    package_name = Column(String(100))
    app_version = Column(String(50))
    activites = Column(Text)
    created_date = Column(DateTime, default=datetime.datetime.now)


class HisPermissionTable(Base):
    __tablename__ = "history_permission"
    his_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    package_name = Column(String(100))
    app_version = Column(String(50))
    permissions = Column(Text)
    created_date = Column(DateTime, default=datetime.datetime.now)


class HisExecutedTable(Base):
    __tablename__ = "history_executed"
    his_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer)
    package_name = Column(String(100))
    app_version = Column(String(50))
    excuted_methods = Column(Text)
    created_date = Column(DateTime, default=datetime.datetime.now)
