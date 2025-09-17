# app/routes/registro.py
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

def get_or_set_device_cookie(request: Request, response) -> str:
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

@router.get("/registro_dispositivo", response_class=HTMLResponse)
async def registro_dispositivo_get(request: Request):
    # Muestra un form simple para ingresar placa y registrar el dispositivo actual
    return templates.TemplateResponse("registro_dispositivo.html", {"request": request})

@router.post("/registro_dispositivo", response_class=HTMLResponse)
async def registro_dispositivo_post(
    request: Request,
    placa: str = Form(...),
    db: Session = Depends(get_db)
):
    # Preparar respuesta para setear cookie si no existe
    response = RedirectResponse(url=f"/registro_ok?placa={placa}", status_code=303)
    device_id = get_or_set_device_cookie(request, response)

    # Validar placa en lista blanca
    if not crud.placa_autorizada_existe(db, placa):
        return HTMLResponse(
            "<h2 style='color:red'>❌ Placa no autorizada. Contacte a su supervisor.</h2>",
            status_code=403
        )

    # Registrar vínculo dispositivo <-> placa (si no existía)
    if not crud.dispositivo_autorizado_valido(db, device_id, placa):
        crud.registrar_dispositivo_autorizado(db, device_id, placa)

    return response

@router.get("/registro_ok", response_class=HTMLResponse)
async def registro_ok(request: Request, placa: str):
    # Pantalla de éxito
    html = f"""
    <html><body style="font-family:Arial; text-align:center; padding:40px">
      <h2>✅ Dispositivo registrado correctamente</h2>
      <p>Placa autorizada: <b>{placa}</b></p>
      <p>Ya puedes usar los QR operativos.</p>
    </body></html>
    """
    return HTMLResponse(html)