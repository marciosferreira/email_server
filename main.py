import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from db import USERS, get_db, get_user, init_db
from email_router import router as email_router
from agenda_router import router as agenda_router

app = FastAPI(title="Mock Email + Agenda Service — Curso Agentes IA")

app.include_router(email_router)
app.include_router(agenda_router)

init_db()


class LoginRequest(BaseModel):
    token: str
    password: str


@app.post("/auth/login", tags=["Geral"])
def login(payload: LoginRequest):
    user = USERS.get(payload.token)
    if not user:
        raise HTTPException(status_code=401, detail={
            "erro": "Usuário não encontrado.",
            "token_recebido": payload.token,
            "dica": "O token deve ser no formato 'aluno-01' até 'aluno-10'. Consulte GET /users para ver os usuários disponíveis.",
        })
    if payload.password != user["password"]:
        raise HTTPException(status_code=401, detail={
            "erro": "Senha incorreta.",
            "dica": "Verifique a senha enviada para o token informado.",
        })
    return {"token": payload.token, "name": user["name"], "email": user["email"]}


@app.get("/health", tags=["Geral"])
def health():
    with get_db() as conn:
        total_emails = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        total_agenda = conn.execute("SELECT COUNT(*) FROM compromissos").fetchone()[0]
    return {
        "status": "ok",
        "usuarios_registrados": len(USERS),
        "total_mensagens": total_emails,
        "total_compromissos": total_agenda,
    }


@app.get("/me", tags=["Geral"])
def me(request: Request):
    user = get_user(request)
    return {"name": user["name"], "email": user["email"], "token": user["token"]}


@app.get("/users", tags=["Geral"])
def list_users(request: Request):
    get_user(request)
    return [{"name": v["name"], "email": v["email"]} for v in USERS.values()]


_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
