from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.db import Base, Item, SessionLocal, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Evaluation DevOps", lifespan=lifespan)


class ItemIn(BaseModel):
    name: str


@app.get("/")
def root():
    return {"message": "API Evaluation DevOps"}


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ok"}


@app.post("/items", status_code=201)
def create_item(item: ItemIn):
    with SessionLocal() as session:
        db_item = Item(name=item.name)
        session.add(db_item)
        session.commit()
        session.refresh(db_item)
        return {"id": db_item.id, "name": db_item.name}


@app.get("/items")
def list_items():
    with SessionLocal() as session:
        items = session.query(Item).all()
        return [{"id": i.id, "name": i.name} for i in items]