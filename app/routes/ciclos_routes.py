# app/routes/ciclos_routes.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import timezone
from app.database import get_db
from app.utils.timezone import formatear_hora_panama, ahora_panama
from fastapi.templating import Jinja2Templates
from datetime import datetime
import locale

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ======================================================
# 🧭 VISTA PRINCIPAL DE CICLOS ABIERTOS (HTML)
# ======================================================
@router.get("/ciclos", response_class=HTMLResponse)
async def mostrar_ciclos(request: Request):
    try:
        locale.setlocale(locale.LC_TIME, 'es_PA.UTF-8')
    except:
        locale.setlocale(locale.LC_TIME, 'es_ES')

    # ✅ Fecha en formato "Mié 29 oct"
    fecha_actual = datetime.now().strftime("%a %d %b").capitalize()

    # Ya no se incluye "ciclos": ciclos, porque se cargan por fetch desde /api/ciclos
    return templates.TemplateResponse("ciclos.html", {
        "request": request,
        "fecha_actual": fecha_actual
    })

# ======================================================
# 🔹 API: Datos de la vista ciclos_abiertos
# ======================================================
@router.get("/api/ciclos")
async def obtener_ciclos_abiertos(db: Session = Depends(get_db)):
    try:
        query = text("""
            SELECT 
                placa,
                puntos_escaneados,
                inicio_ciclo,
                ultimo_escaneo
            FROM ciclos_abiertos
            ORDER BY ultimo_escaneo DESC;
        """)
        resultados = db.execute(query).fetchall()
    except Exception as e:
        print(f"⚠️ Error al consultar la vista ciclos_abiertos: {e}")
        return JSONResponse(content=[], status_code=500)

    ahora = ahora_panama()
    ciclos = []
    for c in resultados:
        # 🔹 Limpiar puntos escaneados (mostrar solo números únicos en orden)
        if isinstance(c.puntos_escaneados, list):
            puntos = [p for p in c.puntos_escaneados if p.startswith("punto")]
            numeros = sorted({int(p.replace("punto", "")) for p in puntos})
            puntos_str = ", ".join(str(n) for n in numeros)
        elif isinstance(c.puntos_escaneados, str):
            partes = c.puntos_escaneados.split(",")
            numeros = sorted({int(p.replace("punto", "")) for p in partes if "punto" in p})
            puntos_str = ", ".join(str(n) for n in numeros)
        else:
            puntos_str = "-"

        # 🔹 Calcular tiempo total (minutos desde inicio hasta ahora)
        inicio = c.inicio_ciclo.replace(tzinfo=timezone.utc)
        delta_min = (ahora - inicio).total_seconds() / 60
        tiempo_str = f"{int(round(delta_min)):02d} min"

        ciclos.append({
            "placa": c.placa,
            "puntos_escaneados": puntos_str,
            "inicio": formatear_hora_panama(c.inicio_ciclo),
            "ultimo_escaneo": formatear_hora_panama(c.ultimo_escaneo),
            "minutos_transcurridos": tiempo_str
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

    # Acción: eliminar ciclo
    if accion == "eliminar":
        db.execute(text("""
            DELETE FROM escaneos WHERE ciclo_id = :cid;
            DELETE FROM ciclos WHERE id = :cid;
        """), {"cid": ciclo.ciclo_id})
        db.execute(text("""
            INSERT INTO ciclo_manual 
            (placa, fecha_eliminacion, motivo, detalles, sesion_id, ciclo_id, registrado_por)
            VALUES (:placa, NOW(), :motivo, CAST(:detalles AS jsonb), :sid, :cid, :registrado_por);
        """), {
            "placa": placa,
            "motivo": motivo,
            "detalles": detalles or "{}",
            "sid": ciclo.sesion_id,
            "cid": ciclo.ciclo_id,
            "registrado_por": registrado_por
        })
        db.commit()
        print(f"❌ Ciclo eliminado manualmente: {placa} ({motivo}) — {registrado_por}")
        return JSONResponse(content={"success": True, "msg": "Ciclo eliminado correctamente."})

    # Acción: cerrar ciclo
    elif accion == "cerrar":
        db.execute(text("""
            UPDATE ciclos SET completado = TRUE, fin = NOW() WHERE id = :cid;
        """), {"cid": ciclo.ciclo_id})
        db.execute(text("""
            INSERT INTO ciclo_manual 
            (placa, fecha_eliminacion, motivo, detalles, sesion_id, ciclo_id, registrado_por)
            VALUES (:placa, NOW(), :motivo, CAST(:detalles AS jsonb), :sid, :cid, :registrado_por);
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

    else:
        return JSONResponse(status_code=400, content={"error": "Acción no válida."})