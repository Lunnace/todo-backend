from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from openpyxl import Workbook, load_workbook
import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, for development only!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Task(BaseModel):
    description: str
    start_date: str
    deadline: str
    done: bool = False

TASKS_FILE = 'tasks.xlsx'

DATABASE_URL = 'sqlite:///./todo.db'
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    tasks = relationship('Task', back_populates='owner')

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    start_date = Column(String, nullable=False)
    deadline = Column(String, nullable=False)
    done = Column(Boolean, default=False)
    owner_id = Column(Integer, ForeignKey('users.id'))
    owner = relationship('User', back_populates='tasks')

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

Base.metadata.create_all(bind=engine)

def load_tasks_from_excel():
    loaded_tasks = []
    if os.path.exists(TASKS_FILE):
        wb = load_workbook(TASKS_FILE)
        ws = wb.active
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] and row[1] and row[2]:
                done = bool(row[3]) if len(row) > 3 and row[3] is not None else False
                loaded_tasks.append(Task(description=row[0], start_date=row[1], deadline=row[2], done=done))
    return loaded_tasks

def save_tasks_to_excel(tasks):
    wb = Workbook()
    ws = wb.active
    ws.append(["description", "start_date", "deadline", "done"])
    for task in tasks:
        ws.append([task.description, task.start_date, task.deadline, task.done])
    wb.save(TASKS_FILE)

tasks: List[Task] = load_tasks_from_excel()

@app.get("/tasks", response_model=List[Task])
def get_tasks():
    return tasks

@app.post("/tasks", response_model=Task)
def add_task(task: Task):
    tasks.append(task)
    save_tasks_to_excel(tasks)
    return task

@app.delete("/tasks/{task_idx}")
def delete_task(task_idx: int):
    if 0 <= task_idx < len(tasks):
        tasks.pop(task_idx)
        save_tasks_to_excel(tasks)
        return {"message": "Task removed"}
    return {"error": "Invalid index"}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post('/register')
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail='Username already registered')
    new_user = User(username=user.username, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully"}

@app.post('/login')
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username, User.password == user.password).first()
    if not db_user:
        raise HTTPException(status_code=401, detail='Invalid username or password')
    # For simplicity, return username as token (not secure, just for demo)
    return {"token": db_user.username}