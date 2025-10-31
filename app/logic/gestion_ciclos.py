# app/logic/ciclos.py
from datetime import timedelta
from typing import Optional
from sqlalchemy import text
from app import models
from app.utils.timezone import ahora_panama, formatear_hora_panama

def registrar_escaneo(db, device_cookie: str, placa: str, punto: Optional[str] = None, crud_module=None, crear_escaneo: bool = True):
    """
    Registra un escaneo reutilizando ciclos existentes cuando la misma placa escanea
    desde otro dispositivo dentro de la última hora.
    """
    if crud_module is None:
        raise ValueError("crud_module es requerido para registrar escaneos")
    ahora = ahora_panama()
    limite_reutilizacion = ahora - timedelta(minutes=60)

    cookie_canonica = device_cookie
    camion = crud_module.get_camion_by_cookie(db, device_cookie) if device_cookie else None
    sesion = crud_module.get_sesion_activa(db, camion.id) if camion else None
    ciclo = None
    reutilizo = False

    if sesion is None and placa:
        sesion_placa = crud_module.get_sesion_activa_por_placa(db, placa)
        if sesion_placa:
            ciclo_existente = crud_module.get_ciclo_activo(db, sesion_placa.id)
            ultimo_escaneo = None
            if ciclo_existente:
                ultimo_escaneo = crud_module.get_ultimo_escaneo_por_ciclo(db, ciclo_existente.id)
            if (
                ciclo_existente
                and ultimo_escaneo
                and ultimo_escaneo.fecha_hora >= limite_reutilizacion
                and sesion_placa.camion
                and sesion_placa.camion.device_cookie
                and sesion_placa.camion.device_cookie != device_cookie
            ):
                camion = sesion_placa.camion
                sesion = sesion_placa
                ciclo = ciclo_existente
                cookie_canonica = sesion_placa.camion.device_cookie
                reutilizo = True

    if camion is None:
        camion = crud_module.create_camion(db, device_cookie=cookie_canonica)

    if sesion is None:
        sesion = crud_module.create_sesion(db, camion.id, placa)
    elif sesion.camion_id != camion.id:
        sesion.camion_id = camion.id
        db.commit()
        db.refresh(sesion)

    if ciclo is None:
        ciclo = crud_module.get_ciclo_activo(db, sesion.id)
    if ciclo is None:
        ciclo = crud_module.create_ciclo(db, sesion.id)

    escaneo = None
    if crear_escaneo and punto is not None:
        escaneo = crud_module.create_escaneo(db, ciclo.id, punto)

    return {
        "camion": camion,
        "sesion": sesion,
        "ciclo": ciclo,
        "escaneo": escaneo,
        "cookie": cookie_canonica,
        "reutilizado": reutilizo,
    }

def registrar_cierre_ciclo(sesion, hora_cierre):
    """Registra en consola el cierre de un ciclo."""
    print(f"✅ Ciclo completado: Placa {sesion.placa} — {formatear_hora_panama(hora_cierre)}")

def eliminar_ciclo_incompleto(db, ciclo, sesion, crud):
    # 1️⃣ Verificar si ya se registró esta eliminación
    existe = db.execute(text("""
        SELECT id FROM ciclo_manual
        WHERE sesion_id = :sid OR placa = :placa
        ORDER BY id DESC LIMIT 1;
    """), {"sid": sesion.id, "placa": sesion.placa}).fetchone()

    if existe:
        print(f"⚠️ Eliminación ya registrada previamente para {sesion.placa}, no se repite.")
        return  # Evita duplicar el registro

    # 2️⃣ Proceder con eliminación si no existe
    db.query(models.Escaneo).filter(models.Escaneo.ciclo_id == ciclo.id).delete()
    db.delete(ciclo)
    db.commit()

    hora_eliminacion = ahora_panama()
    db.execute(
        text("""
            INSERT INTO ciclo_manual (placa, fecha_eliminacion, sesion_id, ciclo_id, motivo, detalles, registrado_por)
            VALUES (:placa, :fecha_eliminacion, :sesion_id, :ciclo_id, 'Omitió punto3', '{}', 'Sistema');
        """),
        {
            "placa": sesion.placa,
            "fecha_eliminacion": hora_eliminacion,
            "sesion_id": sesion.id,
            "ciclo_id": ciclo.id
        }
    )
    db.commit()
    print(f"🚫 Ciclo eliminado por omitir punto3: Placa {sesion.placa} — {formatear_hora_panama(hora_eliminacion)}")

# =============================================
# 🔹 NUEVAS FUNCIONES PARA GESTIÓN MANUAL DE CICLOS
# =============================================

def cerrar_ciclo_manual(db, ciclo_id, sesion_id, placa, motivo, detalles, registrado_por):
    """Marca el ciclo como completado manualmente y lo registra en ciclo_manual."""
    hora_cierre = ahora_panama()
    db.execute(text("""
        UPDATE ciclos 
        SET completado = TRUE, fin = :hora_cierre
        WHERE id = :ciclo_id
    """), {"hora_cierre": hora_cierre, "ciclo_id": ciclo_id})
    db.commit()

    db.execute(text("""
        INSERT INTO ciclo_manual 
        (placa, fecha_eliminacion, motivo, detalles, sesion_id, ciclo_id, registrado_por)
        VALUES (:placa, :fecha_eliminacion, :motivo, :detalles, :sesion_id, :ciclo_id, :registrado_por)
    """), {
        "placa": placa,
        "fecha_eliminacion": hora_cierre,
        "motivo": motivo,
        "detalles": detalles,
        "sesion_id": sesion_id,
        "ciclo_id": ciclo_id,
        "registrado_por": registrado_por
    })
    db.commit()
    print(f"🟢 Ciclo cerrado manualmente — Placa {placa} — {motivo} — {registrado_por} — {formatear_hora_panama(hora_cierre)}")


def eliminar_ciclo_manual(db, ciclo_id, sesion_id, placa, motivo, detalles, registrado_por):
    """Elimina completamente el ciclo y guarda el registro en ciclo_manual."""
    hora_eliminacion = ahora_panama()

    db.execute(text("""
        INSERT INTO ciclo_manual 
        (placa, fecha_eliminacion, motivo, detalles, sesion_id, ciclo_id, registrado_por)
        VALUES (:placa, :fecha_eliminacion, :motivo, :detalles, :sesion_id, :ciclo_id, :registrado_por)
    """), {
        "placa": placa,
        "fecha_eliminacion": hora_eliminacion,
        "motivo": motivo,
        "detalles": detalles,
        "sesion_id": sesion_id,
        "ciclo_id": ciclo_id,
        "registrado_por": registrado_por
    })
    db.commit()

    db.execute(text("DELETE FROM escaneos WHERE ciclo_id = :ciclo_id"), {"ciclo_id": ciclo_id})
    db.execute(text("DELETE FROM ciclos WHERE id = :ciclo_id"), {"ciclo_id": ciclo_id})
    db.commit()
    print(f"🚫 Ciclo eliminado manualmente — Placa {placa} — {motivo} — {registrado_por} — {formatear_hora_panama(hora_eliminacion)}")
