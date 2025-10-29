# app/routes/ciclos_routes.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.utils.timezone import formatear_hora_panama
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ======================================================
# 🧭 VISTA PRINCIPAL (HTML)
# ======================================================
@router.get("/ciclos", response_class=HTMLResponse)
async def mostrar_ciclos(request: Request):
    """Renderiza la página principal de gestión manual de ciclos."""
    return templates.TemplateResponse("ciclos.html", {"request": request})

# ======================================================
# 📊 API JSON PARA CARGAR DATOS (usa la vista ciclos_abiertos)
# ======================================================
@router.get("/api/ciclos", response_class=JSONResponse)
async def obtener_ciclos_abiertos(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT 
                placa,
                puntos_escaneados,
                inicio_ciclo,
                ultimo_escaneo,
                tiempo_total_min
            FROM ciclos_abiertos
            ORDER BY ultimo_escaneo DESC;
        """)
        ciclos_abiertos = db.execute(query).fetchall()
    except Exception as e:
        print(f"⚠️ Error al consultar la vista ciclos_abiertos: {e}")
        return JSONResponse(content=[])

    ciclos = []
    for c in ciclos_abiertos:
        ciclos.append({
            "placa": c.placa,
            "puntos_escaneados": c.puntos_escaneados,
            "inicio": formatear_hora_panama(c.inicio_ciclo),
            "ultimo_escaneo": formatear_hora_panama(c.ultimo_escaneo),
            "minutos_transcurridos": round(c.tiempo_total_min or 0, 1)
        })

    return JSONResponse(content=ciclos)

# ======================================================
# ⚙️ REGISTRO MANUAL (CERRAR O ELIMINAR)
# ======================================================
@router.post("/ciclos/accion")
async def accion_manual(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    placa = data.get("placa")
    motivo = data.get("motivo")
    detalles = data.get("detalles")
    registrado_por = data.get("registrado_por")
    accion = data.get("accion")

    # Verificar ciclo activo mediante la vista
    ciclo = db.execute(text("""
        SELECT sesion_id, ciclo_id 
        FROM ciclos_abiertos 
        WHERE placa = :placa 
        ORDER BY ultimo_escaneo DESC 
        LIMIT 1;
    """), {"placa": placa}).fetchone()

    if not ciclo:
        return JSONResponse(status_code=404, content={"error": "No se encontró ciclo abierto para esa placa."})

    if accion == "eliminar":
        db.execute(text("DELETE FROM escaneos WHERE ciclo_id = :cid"), {"cid": ciclo.ciclo_id})
        db.execute(text("DELETE FROM ciclos WHERE id = :cid"), {"cid": ciclo.ciclo_id})
        db.execute(text("""
            INSERT INTO ciclos_manual 
            (placa, fecha_eliminacion, motivo, detalles, sesion_id, ciclo_id, registrado_por)
            VALUES (:placa, NOW(), :motivo, :detalles::jsonb, :sid, :cid, :registrado_por)
        """), {
            "placa": placa,
            "motivo": motivo,
            "detalles": detalles or "{}",
            "sid": ciclo.sesion_id,
            "cid": ciclo.ciclo_id,
            "registrado_por": registrado_por
        })
        db.commit()
        print(f"🗑️ Ciclo eliminado manualmente: {placa} ({motivo}) — {registrado_por}")
        return JSONResponse(content={"success": True, "msg": "Ciclo eliminado correctamente."})

    elif accion == "cerrar":
        db.execute(text("UPDATE ciclos SET completado = TRUE, fin = NOW() WHERE id = :cid"), {"cid": ciclo.ciclo_id})
        db.execute(text("""
            INSERT INTO ciclos_manual 
            (placa, fecha_eliminacion, motivo, detalles, sesion_id, ciclo_id, registrado_por)
            VALUES (:placa, NOW(), :motivo, :detalles::jsonb, :sid, :cid, :registrado_por)
        """), {
            "placa": placa,
            "motivo": motivo,
            "detalles": detalles or "{}",
            "sid": ciclo.sesion_id,
            "cid": ciclo.ciclo_id,
            "registrado_por": registrado_por
        })
        db.commit()
        print(f"✅ Ciclo cerrado manualmente: {placa} ({motivo}) — {registrado_por}")
        return JSONResponse(content={"success": True, "msg": "Ciclo cerrado correctamente."})

    return JSONResponse(status_code=400, content={"error": "Acción no válida."})