# aqui se configura la conecxion a la base de datos

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL

# Base de datos
if not DATABASE_URL:
    raise ValueError("❌ No se encontró la variable de entorno DATABASE_URL. Configúrala en Render.")

# Render usa PostgreSQL con SSL obligatorio
engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"} if "render.com" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency injection para FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()