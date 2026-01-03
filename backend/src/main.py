# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from api.routes.api_routes import api_router  # Vérifie que ce fichier existe et que l'import est correct
from database.connection import init_db_pool, ping_db, close_db_pool  # Vérifie que ce fichier existe également


app = FastAPI(title="Auth & Users API")

# Inclusion du routeur API
app.include_router(api_router, prefix="/api")

# Initialisation du Limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Ajout du middleware SlowAPI pour la gestion du taux de requêtes
app.add_middleware(SlowAPIMiddleware)

# Configuration CORS pour autoriser certains domaines
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://ton-front.exemple"],  # Vérifie l'URL du frontend
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Route de base
@app.get("/")
def root():
    return {"message": "Serveur FastAPI lancé"}

# Middleware pour sécuriser les en-têtes HTTP
@app.middleware("http")
async def secure_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    return response

# Gestion des erreurs UnicodeDecodeError
@app.exception_handler(UnicodeDecodeError)
async def unicode_error_handler(request: Request, exc: UnicodeDecodeError):
    return JSONResponse(status_code=400, content={"detail": "Erreur"})

# Gestion des exceptions générales
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

# Gestion de l'événement de démarrage
@app.on_event("startup")
def on_startup():
    try:
        init_db_pool()
        if ping_db():
            print("Serveur démarré — Connexion à PostgreSQL réussie")
        else:
            print("Ping DB a échoué")
    except Exception as e:
        print(f"Échec init pool / connexion DB : {e}")

# Gestion de l'événement d'arrêt
@app.on_event("shutdown")
def on_shutdown():
    close_db_pool()
