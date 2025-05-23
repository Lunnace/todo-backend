from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from openpyxl import Workbook, load_workbook
import os

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