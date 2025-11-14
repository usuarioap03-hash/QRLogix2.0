# app/routes/ciclos_routes.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.utils.timezone import formatear_hora_panama, ahora_panama, convertir_a_panama
from fastapi.templating import Jinja2Templates
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# ======================================================
# 🔹 MODELOS PYDANTIC PARA VALIDACIÓN
# ======================================================
class AccionCicloRequest(BaseModel):
    placa: Optional[str] = None
    placas: Optional[List[str]] = None  # Para acciones múltiples
    motivo: str
    detalles: Optional[str] = ""
    registrado_por: str
    accion: str  # "cerrar" o "eliminar"

# ======================================================
# 🧭 VISTA PRINCIPAL DE CICLOS ABIERTOS (HTML)
# ======================================================
@router.get("/ciclos", response_class=HTMLResponse)
async def mostrar_ciclos(request: Request):
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    ahora = datetime.now()
    fecha_actual = f"{dias[ahora.weekday()]} {ahora.day} {meses[ahora.month - 1]}"

    return templates.TemplateResponse("ciclos.html", {
        "request": request,
        "fecha_actual": fecha_actual.capitalize()
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

        inicio_dt = convertir_a_panama(c.inicio_ciclo)
        ultimo_dt = convertir_a_panama(c.ultimo_escaneo)

        if not inicio_dt or not ultimo_dt:
            continue  # evita filas incompletas

        # 🔹 Calcular tiempo total (minutos desde inicio hasta ahora en Panamá)
        delta_min = (ahora - inicio_dt).total_seconds() / 60
        tiempo_str = f"{int(round(delta_min)):02d} min"

        ciclos.append({
            "placa": c.placa,
            "puntos_escaneados": puntos_str,
            "inicio": formatear_hora_panama(inicio_dt),
            "ultimo_escaneo": formatear_hora_panama(ultimo_dt),
            "minutos_transcurridos": tiempo_str
        })

    return JSONResponse(content=ciclos)

# ======================================================
# ⚙️ REGISTRO MANUAL (CERRAR O ELIMINAR) - OPTIMIZADO
# ======================================================
@router.post("/ciclos/accion")
async def accion_manual(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        
        # Validar datos básicos
        motivo = data.get("motivo")
        detalles = data.get("detalles", "")
        registrado_por = data.get("registrado_por")
        accion = data.get("accion")
        
        if not motivo or not registrado_por or not accion:
            return JSONResponse(
                status_code=400, 
                content={"error": "Faltan campos obligatorios: motivo, registrado_por o acción"}
            )
        
        if accion not in ["cerrar", "eliminar"]:
            return JSONResponse(
                status_code=400, 
                content={"error": "Acción no válida. Debe ser 'cerrar' o 'eliminar'"}
            )
        
        # Determinar si es acción individual o múltiple
        placas = data.get("placas")  # Lista de placas para acción múltiple
        placa_individual = data.get("placa")  # Placa individual
        
        if placas and isinstance(placas, list):
            # 🔹 ACCIÓN MÚLTIPLE
            return await procesar_accion_multiple(
                db, placas, motivo, detalles, registrado_por, accion
            )
        elif placa_individual:
            # 🔹 ACCIÓN INDIVIDUAL
            return await procesar_accion_individual(
                db, placa_individual, motivo, detalles, registrado_por, accion
            )
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "Debe proporcionar 'placa' o 'placas'"}
            )
            
    except Exception as e:
        print(f"❌ Error en accion_manual: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error interno del servidor: {str(e)}"}
        )

# ======================================================
# 🔧 FUNCIÓN AUXILIAR: PROCESAR ACCIÓN INDIVIDUAL
# ======================================================
async def procesar_accion_individual(
    db: Session, 
    placa: str, 
    motivo: str, 
    detalles: str, 
    registrado_por: str, 
    accion: str
):
    """Procesa cerrar o eliminar un ciclo individual"""
    
    # Verificar ciclo activo mediante la vista
    ciclo = db.execute(text("""
        SELECT sesion_id, ciclo_id 
        FROM ciclos_abiertos 
        WHERE placa = :placa 
        ORDER BY ultimo_escaneo DESC 
        LIMIT 1;
    """), {"placa": placa}).fetchone()

    if not ciclo:
        return JSONResponse(
            status_code=404, 
            content={"error": f"No se encontró ciclo abierto para la placa {placa}"}
        )

    try:
        if accion == "eliminar":
            # Eliminar escaneos y ciclo
            db.execute(text("""
                DELETE FROM escaneos WHERE ciclo_id = :cid;
            """), {"cid": ciclo.ciclo_id})
            
            db.execute(text("""
                DELETE FROM ciclos WHERE id = :cid;
            """), {"cid": ciclo.ciclo_id})
            
            # Registrar en ciclo_manual
            db.execute(text("""
                INSERT INTO ciclo_manual 
                (placa, fecha_eliminacion, motivo, detalles, sesion_id, ciclo_id, registrado_por)
                VALUES (:placa, NOW(), :motivo, :detalles, :sid, :cid, :registrado_por);
            """), {
                "placa": placa,
                "motivo": motivo,
                "detalles": detalles or '',
                "sid": ciclo.sesion_id,
                "cid": ciclo.ciclo_id,
                "registrado_por": registrado_por
            })
            
            db.commit()
            print(f"❌ Ciclo eliminado manualmente: {placa} ({motivo}) — {registrado_por}")
            
            return JSONResponse(content={
                "success": True, 
                "msg": f"Ciclo de {placa} eliminado correctamente",
                "placa": placa,
                "accion": "eliminado"
            })

        elif accion == "cerrar":
            # Cerrar ciclo
            db.execute(text("""
                UPDATE ciclos SET completado = TRUE, fin = NOW() WHERE id = :cid;
            """), {"cid": ciclo.ciclo_id})
            
            # Registrar en ciclo_manual
            db.execute(text("""
                INSERT INTO ciclo_manual 
                (placa, fecha_eliminacion, motivo, detalles, sesion_id, ciclo_id, registrado_por)
                VALUES (:placa, NOW(), :motivo, :detalles, :sid, :cid, :registrado_por);
            """), {
                "placa": placa,
                "motivo": motivo,
                "detalles": detalles or '',
                "sid": ciclo.sesion_id,
                "cid": ciclo.ciclo_id,
                "registrado_por": registrado_por
            })
            
            db.commit()
            print(f"✅ Ciclo cerrado manualmente: {placa} ({motivo}) — {registrado_por}")
            
            return JSONResponse(content={
                "success": True, 
                "msg": f"Ciclo de {placa} cerrado correctamente",
                "placa": placa,
                "accion": "cerrado"
            })
            
    except Exception as e:
        db.rollback()
        print(f"❌ Error al procesar {placa}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al procesar {placa}: {str(e)}"}
        )

# ======================================================
# 🔧 FUNCIÓN AUXILIAR: PROCESAR ACCIÓN MÚLTIPLE
# ======================================================
async def procesar_accion_multiple(
    db: Session, 
    placas: List[str], 
    motivo: str, 
    detalles: str, 
    registrado_por: str, 
    accion: str
):
    """Procesa cerrar o eliminar múltiples ciclos"""
    
    resultados = {
        "exitosos": [],
        "fallidos": [],
        "total": len(placas)
    }
    
    for placa in placas:
        try:
            # Verificar ciclo activo
            ciclo = db.execute(text("""
                SELECT sesion_id, ciclo_id 
                FROM ciclos_abiertos 
                WHERE placa = :placa 
                ORDER BY ultimo_escaneo DESC 
                LIMIT 1;
            """), {"placa": placa}).fetchone()

            if not ciclo:
                resultados["fallidos"].append({
                    "placa": placa,
                    "error": "No se encontró ciclo abierto"
                })
                continue

            if accion == "eliminar":
                # Eliminar escaneos y ciclo
                db.execute(text("DELETE FROM escaneos WHERE ciclo_id = :cid"), {"cid": ciclo.ciclo_id})
                db.execute(text("DELETE FROM ciclos WHERE id = :cid"), {"cid": ciclo.ciclo_id})
                
                # Registrar en ciclo_manual
                db.execute(text("""
                    INSERT INTO ciclo_manual 
                    (placa, fecha_eliminacion, motivo, detalles, sesion_id, ciclo_id, registrado_por)
                    VALUES (:placa, NOW(), :motivo, :detalles, :sid, :cid, :registrado_por);
                """), {
                    "placa": placa,
                    "motivo": motivo,
                    "detalles": detalles or '',
                    "sid": ciclo.sesion_id,
                    "cid": ciclo.ciclo_id,
                    "registrado_por": registrado_por
                })
                
                db.commit()
                print(f"❌ Ciclo eliminado (múltiple): {placa} ({motivo}) — {registrado_por}")
                resultados["exitosos"].append({"placa": placa, "accion": "eliminado"})

            elif accion == "cerrar":
                # Cerrar ciclo
                db.execute(text("UPDATE ciclos SET completado = TRUE, fin = NOW() WHERE id = :cid"), {"cid": ciclo.ciclo_id})
                
                # Registrar en ciclo_manual
                db.execute(text("""
                    INSERT INTO ciclo_manual 
                    (placa, fecha_eliminacion, motivo, detalles, sesion_id, ciclo_id, registrado_por)
                    VALUES (:placa, NOW(), :motivo, :detalles, :sid, :cid, :registrado_por);
                """), {
                    "placa": placa,
                    "motivo": motivo,
                    "detalles": detalles or '',
                    "sid": ciclo.sesion_id,
                    "cid": ciclo.ciclo_id,
                    "registrado_por": registrado_por
                })
                
                db.commit()
                print(f"✅ Ciclo cerrado (múltiple): {placa} ({motivo}) — {registrado_por}")
                resultados["exitosos"].append({"placa": placa, "accion": "cerrado"})

        except Exception as e:
            db.rollback()
            print(f"❌ Error al procesar {placa}: {e}")
            resultados["fallidos"].append({
                "placa": placa,
                "error": str(e)
            })
    
    return JSONResponse(content={
        "success": True,
        "msg": f"Procesados {len(resultados['exitosos'])} de {resultados['total']} ciclos",
        "resultados": resultados
    })