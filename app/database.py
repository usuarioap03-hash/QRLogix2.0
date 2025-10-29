# aqui se configura la conecxion a la base de datos

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL, TIMEZONE

# Base de datos
if not DATABASE_URL:
    raise ValueError("❌ No se encontró la variable de entorno DATABASE_URL. Configúrala en Render.")

# Render usa PostgreSQL con SSL obligatorio
engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"} if "render.com" in DATABASE_URL else {}
)

@event.listens_for(engine, "connect", insert=True)
def set_time_zone(dbapi_connection, connection_record):
    """Forza la zona horaria de la sesión de base de datos a América/Panamá."""
    cursor = None
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute(f"SET TIME ZONE '{TIMEZONE}'")
    except Exception:
        # Si la base no soporta la instrucción (ej. SQLite), continuamos sin romper la conexión
        pass
    finally:
        if cursor is not None:
            cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency injection para FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
