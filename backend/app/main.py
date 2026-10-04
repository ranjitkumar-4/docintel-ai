import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes.documents import router as documents_router
from app.routes.investigation import router as investigation_router
from app.routes.conflicts import router as conflicts_router
from app.routes.system import router as system_router, health_check
from app.services.embeddings import EmbeddingConfigurationError
from app.services.answer_generator import AnswerProviderError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("docintel")

app = FastAPI(
    title="DocIntel AI API",
    description="Intelligent Document Investigator — Multi-format document RAG with conflict detection and uncertainty handling",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.CORS_ORIGINS.split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(documents_router)
app.include_router(investigation_router)
app.include_router(conflicts_router)
app.include_router(system_router)

@app.get("/health", include_in_schema=False)
async def root_health_check():
    return await health_check()

@app.on_event("startup")
async def startup_event():
    logger.info("DocIntel AI Backend starting up...")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Vector Database Dir: {settings.CHROMA_PERSIST_DIR}")
    logger.info(f"Document Storage: {settings.UPLOAD_DIR}")
    logger.info("Document library preserved as-is; use the UI seed action or seed_demo.py to load samples.")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception during {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"An internal server error occurred: {str(exc)}"}
    )

@app.exception_handler(EmbeddingConfigurationError)
async def embedding_configuration_error_handler(
    request: Request,
    exc: EmbeddingConfigurationError,
):
    logger.error("Embedding configuration error during %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
    )

@app.exception_handler(AnswerProviderError)
async def answer_provider_error_handler(
    request: Request,
    exc: AnswerProviderError,
):
    logger.error("Answer provider error during %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
