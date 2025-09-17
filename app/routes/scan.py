# app/routes/scan.py
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud
import uuid

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

COOKIE_NAME = "device_id"
COOKIE_MAX_AGE = 365 * 24 * 60 * 60  # 1 año

def ensure_device_cookie(request: Request, response) -> str:
    device_id = request.cookies.get(COOKIE_NAME)
    if not device_id:
        device_id = uuid.uuid4().hex
        response.set_cookie(
            key=COOKIE_NAME,
            value=device_id,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="Lax",
        )
    return device_id

@router.get("/scan/{punto}", response_class=HTMLResponse)
async def scan_qr(request: Request, punto: str, db: Session = Depends(get_db)):
    # Si hay sesión activa por IP (o lo que uses en Camion.dispositivo_id), registra directo
    client_ip = request.client.host
    sesion = crud.get_sesion_activa_por_ip(db, client_ip)
    if sesion:
        crud.create_escaneo(db, sesion.id, punto)
        return RedirectResponse(
            url=f"/confirmacion?punto={punto}&placa={sesion.camion.placa}",
            status_code=303
        )

    # Si no hay sesión → mostrar formulario de placa
    return templates.TemplateResponse("index.html", {
        "request": request,
        "punto": punto,
        "submitted": False
    })

@router.post("/scan/{punto}", response_class=HTMLResponse)
async def scan_qr_post(request: Request, punto: str, plate: str = Form(...), db: Session = Depends(get_db)):
    # Set cookie si no existe
    response = RedirectResponse(url=f"/confirmacion?punto={punto}&placa={plate}", status_code=303)
    device_id = ensure_device_cookie(request, response)

    # Validar que el dispositivo esté autorizado para esa placa
    if not crud.dispositivo_autorizado_valido(db, device_id, plate):
        return HTMLResponse(
            "<h2 style='color:red'>❌ Dispositivo o placa no autorizados. Regístrese en capacitación.</h2>",
            status_code=403
        )

    # Flujo normal: crear camión si no existe
    client_ip = request.client.host
    camion = crud.get_camion_by_placa(db, plate)
    if not camion:
        camion = crud.create_camion(db, plate, dispositivo_id=client_ip)

    # Buscar sesión activa; si no existe, crearla
    sesion = crud.get_sesion_activa_por_ip(db, client_ip)
    if not sesion:
        sesion = crud.create_sesion(db, camion.id)  # usa minutos desde config

    # Registrar escaneo
    crud.create_escaneo(db, sesion.id, punto)

    return response