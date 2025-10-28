# app/routes/ciclos.py
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.utils.timezone import ahora_panama
from app.logic import gestion_ciclos as ciclos_logic
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ======================================================
# 🧭 VISTA PRINCIPAL DE CICLOS ABIERTOS
# ======================================================
@router.get("/ciclos", response_class=HTMLResponse)
async def mostrar_ciclos(request: Request, db: Session = Depends(get_db)):
    query = text("""
        SELECT s.placa,
               ARRAY_AGG(e.punto ORDER BY e.fecha_hora) AS puntos_escaneados,
               MIN(e.fecha_hora) AS inicio,
               MAX(e.fecha_hora) AS ultimo_escaneo,
               EXTRACT(EPOCH FROM (MAX(e.fecha_hora) - MIN(e.fecha_hora))) / 60 AS minutos_transcurridos
        FROM ciclos c
        JOIN escaneos e ON e.ciclo_id = c.id
        JOIN sesiones s ON s.id = c.sesion_id
        WHERE c.completado = FALSE
        GROUP BY s.placa, c.id
        ORDER BY inicio ASC;
    """)
    ciclos_abiertos = db.execute(query).fetchall()

    ciclos = []
    for c in ciclos_abiertos:
        ciclos.append({
            "placa": c.placa,
            "puntos_escaneados": c.puntos_escaneados,
            "inicio": c.inicio,
            "ultimo_escaneo": c.ultimo_escaneo,
            "minutos_transcurridos": c.minutos_transcurridos
        })

    return templates.TemplateResponse("ciclos.html", {"request": request, "ciclos": ciclos})


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
    fecha = ahora_panama()

    # Obtener sesión y ciclo activos
    sesion = db.execute(text("SELECT id FROM sesiones WHERE placa = :placa ORDER BY inicio DESC LIMIT 1"), {"placa": placa}).fetchone()
    if not sesion:
        return JSONResponse(status_code=404, content={"error": "No se encontró sesión activa para esa placa."})
    
    ciclo = db.execute(text("SELECT id FROM ciclos WHERE sesion_id = :sesion_id AND completado = FALSE ORDER BY inicio DESC LIMIT 1"), {"sesion_id": sesion.id}).fetchone()
    if not ciclo:
        return JSONResponse(status_code=404, content={"error": "No hay ciclo activo para esa placa."})

    # Acción: eliminar ciclo
    if accion == "eliminar":
        db.execute(text("DELETE FROM escaneos WHERE ciclo_id = :cid"), {"cid": ciclo.id})
        db.execute(text("DELETE FROM ciclos WHERE id = :cid"), {"cid": ciclo.id})
        db.execute(text("""
            INSERT INTO ciclos_manual (placa, fecha_eliminacion, motivo, detalles, sesion_id, ciclo_id, registrado_por)
            VALUES (:placa, :fecha, :motivo, :detalles::jsonb, :sid, :cid, :registrado_por)
        """), {
            "placa": placa,
            "fecha": fecha,
            "motivo": motivo,
            "detalles": detalles or "{}",
            "sid": sesion.id,
            "cid": ciclo.id,
            "registrado_por": registrado_por
        })
        db.commit()
        print(f"🗑️ Ciclo eliminado manualmente: {placa} ({motivo}) — {registrado_por}")
        return JSONResponse(content={"success": True, "msg": "Ciclo eliminado correctamente."})

    # Acción: cerrar ciclo
    elif accion == "cerrar":
        db.execute(text("""
            UPDATE ciclos SET completado = TRUE, fin = :fecha WHERE id = :cid
        """), {"fecha": fecha, "cid": ciclo.id})
        db.execute(text("""
            INSERT INTO ciclos_manual (placa, fecha_eliminacion, motivo, detalles, sesion_id, ciclo_id, registrado_por)
            VALUES (:placa, :fecha, :motivo, :detalles::jsonb, :sid, :cid, :registrado_por)
        """), {
            "placa": placa,
            "fecha": fecha,
            "motivo": motivo,
            "detalles": detalles or "{}",
            "sid": sesion.id,
            "cid": ciclo.id,
            "registrado_por": registrado_por
        })
        db.commit()
        print(f"✅ Ciclo cerrado manualmente: {placa} ({motivo}) — {registrado_por}")
        return JSONResponse(content={"success": True, "msg": "Ciclo cerrado correctamente."})

    else:
        return JSONResponse(status_code=400, content={"error": "Acción no válida."})