import os
import time

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel
from sqlalchemy import text

from app.db import Base, Item, SessionLocal, engine

# Les 3 metriques demandees
REQUETES = Counter("http_requests_total", "Nombre de requetes", ["endpoint", "code"])
LATENCE = Histogram("http_request_duration_seconds", "Duree des requetes", ["endpoint"])
VERSION = Gauge("app_version_info", "Commit deploye", ["commit"])
VERSION.labels(commit=os.getenv("GIT_SHA", "local")).set(1)

app = FastAPI(title="Evaluation DevOps")


@app.on_event("startup")
def demarrage():
    Base.metadata.create_all(bind=engine)


# Mesure chaque requete
@app.middleware("http")
async def mesurer(request: Request, call_next):
    debut = time.time()
    response = await call_next(request)
    duree = time.time() - debut
    route = request.url.path
    REQUETES.labels(endpoint=route, code=response.status_code).inc()
    LATENCE.labels(endpoint=route).observe(duree)
    return response


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
        nouvel_item = Item(name=item.name)
        session.add(nouvel_item)
        session.commit()
        return {"id": nouvel_item.id, "name": nouvel_item.name}


@app.get("/items")
def list_items():
    with SessionLocal() as session:
        items = session.query(Item).all()
        return [{"id": i.id, "name": i.name} for i in items]


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)