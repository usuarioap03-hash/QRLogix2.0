# app/routes/scan.py

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud
from app.utils.timezone import convertir_a_panama, ahora_panama
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
    device_id = request.cookies.get(COOKIE_NAME)
    sesion = crud.get_sesion_activa_por_cookie(db, device_id)

    if sesion:
        escaneo = crud.create_escaneo(db, sesion.id, punto)

        estados = {}
        puntos_list = ["punto1", "punto2", "punto3", "punto4"]
        puntos_escaneados = [e.punto for e in sesion.escaneos]

        for idx, p in enumerate(puntos_list, start=1):
            if p in puntos_escaneados:
                estados[p] = "completed"
            elif f"punto{idx+1}" in puntos_escaneados:
                estados[p] = "skipped"
            else:
                estados[p] = "pending"

        # Si es el último punto, cerrar ciclo (sesión)
        if punto == "punto4":
            sesion.fin = ahora_panama()
            db.commit()

        return templates.TemplateResponse("confirmacion.html", {
            "request": request,
            "punto": punto,
            "placa": sesion.camion.placa,
            "hora": convertir_a_panama(escaneo.fecha_hora).strftime("%-I:%M:%S %p"),
            "puntos": puntos_list,
            "estados": estados,
            "nombres": {
                "punto1": "Ingreso",
                "punto2": "Espera",
                "punto3": "Carga",
                "punto4": "Salida"
            }
        })

    return templates.TemplateResponse("index.html", {
        "request": request,
        "punto": punto,
        "submitted": False
    })