# punto de entrada de FastAPI
# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.routes import scan

# Crear la app FastAPI con metadata
app = FastAPI(
    title="QRLogix",
    description="Sistema de registro de camiones y puntos QR para trazabilidad en planta",
    version="3.1.0"
)

# Archivos estáticos (logo, CSS, etc.)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configuración de CORS (puedes limitar dominios si quieres más seguridad)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # o especificar ["https://midominio.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir las rutas de escaneo
app.include_router(scan.router)

# Healthcheck (para Render y monitoreo)
@app.get("/health")
def healthcheck():
    return {"status": "ok", "service": "QRLogix"}