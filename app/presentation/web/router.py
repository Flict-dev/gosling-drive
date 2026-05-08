from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/presentation/web/templates")
router = APIRouter(tags=["web"])


@router.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/share/{token}")
def public_share_page(request: Request, token: str):
    return templates.TemplateResponse("public_share.html", {"request": request, "token": token})

