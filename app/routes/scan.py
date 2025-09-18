# app/routes/scan.py
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud
from app.utils.timezone import convertir_a_panama
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
    client_ip = request.client.host
    sesion = crud.get_sesion_activa_por_ip(db, client_ip)
    if sesion:
        escaneo = crud.create_escaneo(db, sesion.id, punto)
        estados = {}
        for idx, p in enumerate(["punto1", "punto2", "punto3", "punto4"], start=1):
            if any(e.punto == p for e in sesion.escaneos):
                estados[p] = "completed"
            elif any(e.punto == f"punto{idx+1}" for e in sesion.escaneos):
                estados[p] = "skipped"
            else:
                estados[p] = "pending"
        return templates.TemplateResponse("confirmacion.html", {
            "request": request,
            "punto": punto,
            "placa": sesion.camion.placa,
            "hora": convertir_a_panama(escaneo.fecha_hora).strftime("%I:%M:%p"),
            "puntos": ["punto1", "punto2", "punto3", "punto4"],
            "estados": estados,
            "nombres": {"punto1": "Ingreso", "punto2": "Carga", "punto3": "Salida patio", "punto4": "Control final"}
        })

    return templates.TemplateResponse("index.html", {
        "request": request,
        "punto": punto,
        "submitted": False
    })

@router.post("/scan/{punto}", response_class=HTMLResponse)
async def scan_qr_post(request: Request, punto: str, plate: str = Form(...), db: Session = Depends(get_db)):
    response = RedirectResponse(url=f"/scan/{punto}?placa={plate}", status_code=303)
    ensure_device_cookie(request, response)

    client_ip = request.client.host
    camion = crud.get_camion_by_placa(db, plate)
    if not camion:
        camion = crud.create_camion(db, plate, dispositivo_id=client_ip)

    sesion = crud.get_sesion_activa_por_ip(db, client_ip)
    if not sesion:
        sesion = crud.create_sesion(db, camion.id)

    crud.create_escaneo(db, sesion.id, punto)

    return response