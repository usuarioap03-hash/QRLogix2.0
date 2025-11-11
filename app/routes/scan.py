from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud
from app.utils.timezone import ahora_panama, formatear_hora_panama
import uuid
from app import config
from app.logic.mensajes import obtener_mensaje
from app.logic.gestion_ciclos import eliminar_ciclo_incompleto
from app.logic.gestion_ciclos import registrar_cierre_ciclo, registrar_escaneo

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

COOKIE_NAME = "device_cookie"
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
    if config.MANTENIMIENTO:
        return templates.TemplateResponse("mantenimiento.html", {"request": request})

    device_id = request.cookies.get(COOKIE_NAME)
    camion = crud.get_camion_by_cookie(db, device_id)

    if not camion:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "punto": punto,
            "submitted": False,
            "ZONAA_LAT": config.ZONA_LAT,
            "ZONA_LON": config.ZONA_LON,
            "ZONA_METROS": config.ZONA_METROS,
            "VALIDAR_GEOZONA": config.VALIDAR_GEOZONA,
        })

    sesion = crud.get_sesion_activa(db, camion.id)
    if not sesion:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "punto": punto,
            "submitted": False,
            "ZONA_LAT": config.ZONA_LAT,
            "ZONA_LON": config.ZONA_LON,
            "ZONA_METROS": config.ZONA_METROS,
            "VALIDAR_GEOZONA": config.VALIDAR_GEOZONA,
        })

    registro = registrar_escaneo(
        db=db,
        device_cookie=device_id,
        placa=sesion.placa,
        punto=punto,
        crud_module=crud,
    )
    sesion = registro["sesion"]
    ciclo = registro["ciclo"]
    escaneo = registro["escaneo"]
    cookie_canonica = registro["cookie"]

    if punto == "punto5":
        if not any(e.punto == "punto3" for e in ciclo.escaneos):
            eliminar_ciclo_incompleto(db, ciclo, sesion, crud)
            response = templates.TemplateResponse("confirmacion_salida.html", {
                "request": request,
                "punto": punto,
                "placa": sesion.placa,
                "hora": formatear_hora_panama(escaneo.fecha_hora),
            })
            if cookie_canonica and cookie_canonica != device_id:
                response.set_cookie(
                    key=COOKIE_NAME,
                    value=cookie_canonica,
                    max_age=COOKIE_MAX_AGE,
                    httponly=True,
                    samesite="Lax",
                )
            return response
        else:
            ciclo.fin = ahora_panama()
            ciclo.completado = True
            db.commit()
            registrar_cierre_ciclo(sesion, ciclo.fin)
            hora_cierre = formatear_hora_panama(ciclo.fin)
            print(f"✅ Ciclo completado: Placa {sesion.placa} — {hora_cierre}")
            seleccionado = obtener_mensaje("recordatorio")
            response = templates.TemplateResponse("confirmacion_salida.html", {
                "request": request,
                "punto": punto,
                "placa": sesion.placa,
                "hora": hora_cierre,
            })
            if cookie_canonica and cookie_canonica != device_id:
                response.set_cookie(
                    key=COOKIE_NAME,
                    value=cookie_canonica,
                    max_age=COOKIE_MAX_AGE,
                    httponly=True,
                    samesite="Lax",
                )
            return response

    estados = {}
    puntos_list = ["punto1", "punto2", "punto3", "punto4", "punto5"]
    for idx, p in enumerate(puntos_list, start=1):
        if any(e.punto == p for e in ciclo.escaneos):
            estados[p] = "completed"
        elif any(e.punto == f"punto{idx+1}" for e in ciclo.escaneos):
            estados[p] = "skipped"
        else:
            estados[p] = "pending"

    # 🟢 Mensajes dinámicos (recordatorios o mensajes generales)
    modo = "recordatorio"  # Cambiar a "mensaje" cuando se deseen mensajes fijos

    seleccionado = obtener_mensaje("recordatorio")

    response = templates.TemplateResponse("confirmacion.html", {
        "request": request,
        "punto": punto,
        "placa": sesion.placa,  # ahora viene de Sesion
        "hora": formatear_hora_panama(escaneo.fecha_hora),
        "puntos": puntos_list,
        "estados": estados,
        "nombres": {"punto1": "Patio", "punto2": "Espera", "punto3": "Cargando", "punto4": "Lona", "punto5": "Salida"},
        "modo": modo,
        "mensaje_titulo": seleccionado["titulo"],
        "mensaje_texto": seleccionado["texto"],
        "ilustracion": seleccionado["imagen"],
    })
    if cookie_canonica and cookie_canonica != device_id:
        response.set_cookie(
            key=COOKIE_NAME,
            value=cookie_canonica,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="Lax",
        )
    return response

@router.post("/scan/{punto}", response_class=HTMLResponse)
async def scan_qr_post(request: Request, punto: str, plate: str = Form(...), db: Session = Depends(get_db)):

    response = RedirectResponse(url=f"/scan/{punto}?placa={plate}", status_code=303)
    device_id = ensure_device_cookie(request, response)

    # convertir la placa a mayúsculas
    plate = plate.upper()

    registro = registrar_escaneo(
        db=db,
        device_cookie=device_id,
        placa=plate,
        punto=punto,
        crud_module=crud,
        crear_escaneo=False,
    )

    sesion = registro["sesion"]
    ciclo = registro["ciclo"]
    cookie_canonica = registro["cookie"]

    if cookie_canonica and cookie_canonica != device_id:
        response.set_cookie(
            key=COOKIE_NAME,
            value=cookie_canonica,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="Lax",
        )

    if punto == "punto5":
        if not any(e.punto == "punto3" for e in ciclo.escaneos):
            eliminar_ciclo_incompleto(db, ciclo, sesion, crud)
            return RedirectResponse(url="/", status_code=303)

    crud.create_escaneo(db, ciclo.id, punto)
    return response


# Ruta para mostrar la página de geozona
@router.get("/geozona", response_class=HTMLResponse)
async def mostrar_geozona(request: Request):
    return templates.TemplateResponse("geozona.html", {"request": request})
