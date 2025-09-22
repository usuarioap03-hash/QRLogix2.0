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
    """Genera o recupera un cookie único para identificar el dispositivo."""
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

    if sesion and ahora_panama() <= sesion.fin and not sesion.cerrada:
        # Registrar escaneo
        escaneo = crud.create_escaneo(db, sesion.id, punto)

        # Estados de la barra de progreso
        estados = {}
        puntos_list = ["punto1", "punto2", "punto3", "punto4"]
        ya = [e.punto for e in sesion.escaneos]

        for idx, p in enumerate(puntos_list, start=1):
            if p in ya:
                estados[p] = "completed"
            elif f"punto{idx+1}" in ya:
                estados[p] = "skipped"
            else:
                estados[p] = "pending"

        # Si es el último punto, cerrar ciclo
        if punto == "punto4":
            sesion.fin = ahora_panama()
            sesion.cerrada = True
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

    # Si no hay sesión activa, pedir placa
    return templates.TemplateResponse("index.html", {
        "request": request,
        "punto": punto,
        "submitted": False
    })


@router.post("/scan/{punto}", response_class=HTMLResponse)
async def scan_qr_post(
    request: Request,
    punto: str,
    plate: str = Form(...),
    db: Session = Depends(get_db)
):
    response = RedirectResponse(url=f"/scan/{punto}?placa={plate}", status_code=303)
    device_id = ensure_device_cookie(request, response)

    camion = crud.get_camion_by_placa(db, plate)
    if not camion:
        camion = crud.create_camion(db, plate, device_cookie=device_id)

    sesion = crud.get_sesion_activa_por_cookie(db, device_id)

    # Reusar sesión si está activa y no cerrada
    if sesion and ahora_panama() <= sesion.fin and not sesion.cerrada:
        puntos_escaneados = [e.punto for e in sesion.escaneos]
        if "punto4" in puntos_escaneados:
            # Nuevo ciclo si ya se cerró en el último punto
            sesion = crud.create_sesion(db, camion.id)
    else:
        sesion = crud.create_sesion(db, camion.id)

    crud.create_escaneo(db, sesion.id, punto)

    return response