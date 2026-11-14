from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importamos los módulos de rutas de la aplicación.
from app.routers import (
    health,
    observations,
    objects,
    irsa,
    frames,
    science_preview,
    sia,
    remote_previews,
)

# Importamos la configuración centralizada.
from app.core.config import get_cors_origins


# Creamos la aplicación principal de FastAPI.
app = FastAPI(
    title="ETER API",
    description="Backend científico de ETER",
    version="0.1.0",
)

# Configuramos CORS utilizando los orígenes definidos
# en las variables de entorno o los valores locales.
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Content-Type", "Authorization"],
)

# Registramos los routers de la API.
app.include_router(health.router)
app.include_router(observations.router)
app.include_router(objects.router)
app.include_router(irsa.router)
app.include_router(frames.router)
app.include_router(science_preview.router)
app.include_router(sia.router)
app.include_router(remote_previews.router)
