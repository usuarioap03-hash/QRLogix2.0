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

    # Si hay sesión y NO está expirada, registrar y confirmar
    if sesion and ahora_panama() <= sesion.fin:
        escaneo = crud.create_escaneo(db, sesion.id, punto)

        # Construir estados (completed/skipped/pending) de manera determinista
        puntos_list = ["punto1", "punto2", "punto3", "punto4"]
        ya = {e.punto for e in sesion.escaneos}
        ya.add(punto)  # asegura incluir el recién creado

        estados = {}
        for idx, p in enumerate(puntos_list, start=1):
            if p in ya:
                estados[p] = "completed"
            elif any(f"punto{idx+1}" in ya):
                estados[p] = "skipped"
            else:
                estados[p] = "pending"

        # Si es el último punto, cerrar ciclo
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
            "nombres": {"punto1": "Ingreso", "punto2": "Espera", "punto3": "Carga", "punto4": "Salida"}
        })

    # Si no hay sesión activa o está expirada → pedir placa
    return templates.TemplateResponse("index.html", {
        "request": request,
        "punto": punto,
        "submitted": False
    })

@router.post("/scan/{punto}", response_class=HTMLResponse)
async def scan_qr_post(request: Request, punto: str, plate: str = Form(...), db: Session = Depends(get_db)):
    response = RedirectResponse(url=f"/scan/{punto}?placa={plate}", status_code=303)
    device_cookie = ensure_device_cookie(request, response)

    # Camión por placa; si no existe, lo creamos guardando la cookie
    camion = crud.get_camion_by_placa(db, plate)
    if not camion:
        camion = crud.create_camion(db, plate, device_cookie=device_cookie)

    # Ver si ya hay sesión activa para esa cookie
    sesion = crud.get_sesion_activa_por_cookie(db, device_cookie)

    # Si hay sesión activa pero ya llegó al último punto, arrancar un nuevo ciclo
    if sesion and ahora_panama() <= sesion.fin:
        puntos_escaneados = {e.punto for e in sesion.escaneos}
        if "punto4" in puntos_escaneados:
            sesion = crud.create_sesion(db, camion.id)
    else:
        # Expirada o inexistente → nueva sesión
        sesion = crud.create_sesion(db, camion.id)

    crud.create_escaneo(db, sesion.id, punto)
    return response