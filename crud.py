from http.client import HTTPException
from sqlalchemy.orm import Session
from models import User, Annotation
from sqlalchemy import text


def create_user(db: Session, user):
    db_user = User(username=user.username, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User created"}

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if not user or user.password != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"message": "Login successful"}

def save_annotation(db: Session, ann):
    annotation = Annotation(
        username=ann.username,
        start_time=ann.start_time,
        end_time=ann.end_time,
        label=ann.label,
        type=ann.type,
        description=ann.description
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return {"message": "Annotation saved"}

def get_annotations(db, username, type):
    query = text("""
        SELECT * FROM annotations
        WHERE username = :username AND type = :type
    """)
    result = db.execute(query, {"username": username, "type": type}).fetchall()
    return [dict(row) for row in result]


def fetch_data(db: Session, username: str, datatype: str):
    table_name = f"{username}_{datatype}"
    query = f"SELECT * FROM {table_name}"
    return db.execute(text(query)).fetchall()

def compare_stress_windows(db: Session, username: str, intervention: str, metric: str):
    return {"message": f"Compared stress for {intervention} and metric {metric}"}

def update_annotation(db, ann):
    query = text("""
        UPDATE annotations
        SET start_time = :start_time,
            end_time = :end_time,
            label = :label,
            type = :type,
            description = :description
        WHERE id = :id
    """)
    db.execute(query, ann.dict())
    db.commit()
    return {"message": "Annotation updated"}

def delete_annotation(db, id):
    query = text("DELETE FROM annotations WHERE id = :id")
    db.execute(query, {"id": id})
    db.commit()
    return {"message": "Annotation deleted"}
