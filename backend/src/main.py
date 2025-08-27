# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from api.routes.api_routes import api_router
from database.connection import init_db_pool, ping_db, close_db_pool



app = FastAPI(title="Auth & Users API")

app.include_router(api_router, prefix="/api")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


app.add_middleware(
    CORSMiddleware,
     allow_origins=["http://localhost:3000", "https://ton-front.exemple"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.get("/")
def root():
    return {"message": "Serveur FastAPI lance "}


@app.middleware("http")
async def secure_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers[
        "Content-Security-Policy"
    ] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    return response



@app.exception_handler(UnicodeDecodeError)
async def unicode_error_handler(request: Request, exc: UnicodeDecodeError):
    return JSONResponse(status_code=400, content={"detail": "Erreur"})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    try:
        msg = str(exc)
    except Exception:
        msg = "Erreur"
    low = msg.lower()
    if "utf-8" in low and "codec" in low and "decode" in low:
        msg = "Erreur"
    return JSONResponse(status_code=400, content={"detail": msg})


@app.on_event("startup")
def on_startup():
    try:
        init_db_pool()            
        if ping_db():
            print("Serveur demarre — Connexion a PostgreSQL reussie")
        else:
            print("Ping DB a echoue")
    except Exception:
        print("Echec init pool / connexion DB")

@app.on_event("shutdown")
def on_shutdown():
    close_db_pool()
