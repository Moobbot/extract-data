import sqlite3
import os
from datetime import datetime
from app.core.config import settings

DB_PATH = os.path.join(settings.OUTPUT_DIR, "tasks.sqlite3")

def get_db():
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            filename TEXT,
            template TEXT,
            status TEXT,
            created_at DATETIME,
            completed_at DATETIME,
            json_path TEXT,
            excel_path TEXT,
            error TEXT,
            folder_path TEXT
        )
    """)
    # Try to add folder_path column if table already existed without it
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN folder_path TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def insert_task(task_id: str, filename: str, template: str, folder_path: str = None):
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO tasks (id, filename, template, status, created_at, folder_path)
        VALUES (?, ?, ?, 'pending', ?, ?)
    """, (task_id, filename, template, now, folder_path))
    conn.commit()
    conn.close()

def update_task_status(task_id: str, status: str, json_path: str = None, excel_path: str = None, error: str = None):
    conn = get_db()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    updates = ["status = ?", "completed_at = ?"]
    params = [status, now]
    
    if json_path:
        updates.append("json_path = ?")
        params.append(json_path)
    if excel_path:
        updates.append("excel_path = ?")
        params.append(excel_path)
    if error:
        updates.append("error = ?")
        params.append(error)
        
    params.append(task_id)
    
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, tuple(params))
    conn.commit()
    conn.close()

def get_all_tasks():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
