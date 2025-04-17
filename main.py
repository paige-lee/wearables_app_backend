from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List
import shutil
import os
from fastapi.responses import JSONResponse
import io
import sys
from sqlalchemy import text
from fastapi.middleware.gzip import GZipMiddleware

from database import SessionLocal, engine
import models, crud, utils


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Add GZip middleware to compress responses larger than 10000 bytes
app.add_middleware(GZipMiddleware, minimum_size=10000)

# CORS: allow frontend (localhost:3000) to access the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== AUTH ROUTES ==========

class UserCreate(BaseModel):
    username: str
    password: str

@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db=db, user=user)

@app.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    auth_result = crud.authenticate_user(db, user.username, user.password)
    
    # Clean existing user tables on login
    if auth_result:
        try:
            for table in ["daily_heart_rate", "stress", "respiration", "sleep_respiration"]:
                db.execute(text(f"DROP TABLE IF EXISTS {user.username}_{table}"))
                db.commit()
        except Exception as e:
            print(f"Error clearing old data: {e}")

    return auth_result


# ========== FILE UPLOAD ==========

@app.post("/upload")
def upload_file(username: str = Form(...), file: UploadFile = File(...)):
    file_location = f"temp/{file.filename}"
    os.makedirs("temp", exist_ok=True)

    with open(file_location, "wb+") as f:
        shutil.copyfileobj(file.file, f)

    # Capture stdout logs
    old_stdout = sys.stdout
    sys.stdout = mystdout = io.StringIO()

    try:
        utils.process_local_zip(file_location, username)
        sys.stdout = old_stdout
        log_output = mystdout.getvalue()
        return JSONResponse(content={"message": "✅ Data upload complete!", "log": log_output})
    except Exception as e:
        sys.stdout = old_stdout
        return JSONResponse(status_code=500, content={"message": "Processing failed", "log": str(e)})
    
# ========== ANNOTATION ==========

class Annotation(BaseModel):
    username: str
    start_time: str
    end_time: str
    label: str
    type: str  # 'event' or 'intervention'
    description: str

class AnnotationUpdate(BaseModel):
    id: int  
    username: str
    start_time: str
    end_time: str
    label: str
    type: str
    description: str

@app.post("/add-annotation")
def add_annotation(ann: Annotation, db: Session = Depends(get_db)):
    return crud.save_annotation(db, ann)

@app.get("/annotations/{username}/{type}")
def get_annotations(username: str, type: str, db: Session = Depends(get_db)):
    return crud.get_annotations(db, username, type)

@app.put("/update-annotation")
def update_annotation(ann: AnnotationUpdate, db: Session = Depends(get_db)):
    return crud.update_annotation(db, ann)

@app.delete("/delete-annotation/{id}")
def delete_annotation(id: int, db: Session = Depends(get_db)):
    return crud.delete_annotation(db, id)


# ========== DATA FETCHING ==========

@app.get("/data/{username}/{datatype}")
def get_user_data(username: str, datatype: str, db: Session = Depends(get_db)):
    return crud.fetch_data(db, username, datatype)

@app.get("/all-data/{username}")
def get_all_user_data(username: str, db: Session = Depends(get_db)):
    def get_table(name, fields="*"):
        try:
            query = f"""
                SELECT {fields}
                FROM {username}_{name}
                ORDER BY timestamp_cleaned ASC
            """
            result = db.execute(text(query)).fetchall()
            return [dict(row) for row in result]
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            return []

    return JSONResponse(content={
        "daily_heart_rate": get_table("daily_heart_rate", "timestamp_cleaned, beatsPerMinute"),
        "stress": get_table("stress", "timestamp_cleaned, stressLevel"),
        "respiration": get_table("respiration", "timestamp_cleaned, breathsPerMinute"),
        "sleep_respiration": get_table("sleep_respiration", "timestamp_cleaned, breathsPerMinute"),
    })



# ========== INTERVENTION ANALYSIS ==========

@app.get("/compare/{username}/{intervention}/{metric}")
def compare_intervention(username: str, intervention: str, metric: str, db: Session = Depends(get_db)):
    return crud.compare_stress_windows(db, username, intervention, metric)

