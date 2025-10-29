# app/logic/ciclos.py
from sqlalchemy import text
from app import models
from app.utils.timezone import ahora_panama, formatear_hora_panama

def eliminar_ciclo_incompleto(db, ciclo, sesion, crud):
    # Eliminar escaneos relacionados sin warnings
    db.query(models.Escaneo).filter(models.Escaneo.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.delete(ciclo)
    db.commit()

    hora_eliminacion = ahora_panama()
    db.execute(
        text("INSERT INTO ciclo_manual (placa, fecha_eliminacion) VALUES (:placa, :fecha_eliminacion)"),
        {"placa": sesion.placa, "fecha_eliminacion": hora_eliminacion}
    )
    db.commit()

    print(f"🚫 Ciclo eliminado por omitir punto3: Placa {sesion.placa} — {formatear_hora_panama(hora_eliminacion)}")

def registrar_cierre_ciclo(sesion, hora_cierre):
    print(f"✅ Ciclo completado: Placa {sesion.placa} — {formatear_hora_panama(hora_cierre)}")

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
