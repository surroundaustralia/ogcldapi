import fastapi
from fastapi import Request
from api.collections import CollectionsRenderer

router = fastapi.APIRouter()


@router.get("/collections")
def collection(request: Request):
    return CollectionsRenderer(request).render()
