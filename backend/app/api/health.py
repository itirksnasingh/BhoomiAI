from fastapi import APIRouter


router = APIRouter(tags=["System"])


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "bhoomiai-api",
        "version": "0.1.0",
    }