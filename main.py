"""
Serviço de Email Mock — Curso Agentes IA
Backend completo com SQLite para persistência.
Suporta múltiplos destinatários (To + CC).
"""

import os
import uuid
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Mock Email Service — Curso Agentes IA")

# ---------------------------------------------------------
# Usuários registrados (fixos)
# ---------------------------------------------------------

USERS = {
    "aluno-01": {"name": "Aluno 1",  "email": "aluno01@curso.ia", "password": "1234"},
    "aluno-02": {"name": "Aluno 2",  "email": "aluno02@curso.ia", "password": "1234"},
    "aluno-03": {"name": "Aluno 3",  "email": "aluno03@curso.ia", "password": "1234"},
    "aluno-04": {"name": "Aluno 4",  "email": "aluno04@curso.ia", "password": "1234"},
    "aluno-05": {"name": "Aluno 5",  "email": "aluno05@curso.ia", "password": "1234"},
    "aluno-06": {"name": "Aluno 6",  "email": "aluno06@curso.ia", "password": "1234"},
    "aluno-07": {"name": "Aluno 7",  "email": "aluno07@curso.ia", "password": "1234"},
    "aluno-08": {"name": "Aluno 8",  "email": "aluno08@curso.ia", "password": "1234"},
    "aluno-09": {"name": "Aluno 9",  "email": "aluno09@curso.ia", "password": "1234"},
    "aluno-10": {"name": "Aluno 10", "email": "aluno10@curso.ia", "password": "1234"},
}

EMAIL_TO_TOKEN = {v["email"]: k for k, v in USERS.items()}
DB_PATH = os.environ.get("DB_PATH", "email.db")

# ---------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    if os.path.dirname(DB_PATH):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id                   TEXT PRIMARY KEY,
                from_email           TEXT NOT NULL,
                to_emails            TEXT NOT NULL,  -- JSON list, primeiro é o To principal
                cc_emails            TEXT NOT NULL DEFAULT '[]',  -- JSON list
                subject              TEXT NOT NULL,
                body                 TEXT NOT NULL,
                timestamp            TEXT NOT NULL,
                is_read              INTEGER NOT NULL DEFAULT 0,
                deleted_by_sender    INTEGER NOT NULL DEFAULT 0,
                deleted_by_recipient TEXT NOT NULL DEFAULT '[]'  -- JSON list de emails que deletaram
            )
        """)


init_db()

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

import json

def get_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente. Use: Authorization: Bearer <email ou token>")
    credential = auth.removeprefix("Bearer ").strip()
    # aceita email (aluno01@curso.ia) ou token (aluno-01)
    if credential in USERS:
        token = credential
    elif credential in EMAIL_TO_TOKEN:
        token = EMAIL_TO_TOKEN[credential]
    else:
        raise HTTPException(status_code=403, detail=f"Credencial inválida: '{credential}'")
    return {"token": token, **USERS[token]}


def parse_emails(raw: str) -> List[str]:
    """Divide string de emails por vírgula ou ponto-e-vírgula, normaliza."""
    import re
    parts = re.split(r"[,;]", raw)
    return [e.strip().lower() for e in parts if e.strip()]


def is_recipient_of(msg: sqlite3.Row, email: str) -> bool:
    """Verifica se o email é destinatário (To ou CC) da mensagem."""
    to_list = json.loads(msg["to_emails"])
    cc_list = json.loads(msg["cc_emails"])
    return email in to_list or email in cc_list


def has_deleted(msg: sqlite3.Row, email: str) -> bool:
    deleted = json.loads(msg["deleted_by_recipient"])
    return email in deleted


def row_to_dict(msg: sqlite3.Row, my_email: str) -> dict:
    to_list = json.loads(msg["to_emails"])
    cc_list = json.loads(msg["cc_emails"])
    return {
        "id":        msg["id"],
        "from":      msg["from_email"],
        "to":        to_list,
        "cc":        cc_list,
        "subject":   msg["subject"],
        "body":      msg["body"],
        "timestamp": msg["timestamp"],
        "read":      bool(msg["is_read"]),
    }


# ---------------------------------------------------------
# Schemas
# ---------------------------------------------------------

class LoginRequest(BaseModel):
    token: str
    password: str


class SendEmailRequest(BaseModel):
    to: str                      # um ou mais emails separados por , ou ;
    cc: Optional[str] = ""       # um ou mais emails separados por , ou ;
    subject: str
    body: str


# ---------------------------------------------------------
# Auth
# ---------------------------------------------------------

@app.post("/auth/login")
def login(payload: LoginRequest):
    user = USERS.get(payload.token)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")
    if payload.password != user["password"]:
        raise HTTPException(status_code=401, detail="Senha incorreta.")
    return {"token": payload.token, "name": user["name"], "email": user["email"]}


# ---------------------------------------------------------
# Info
# ---------------------------------------------------------

@app.get("/health")
def health():
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    return {"status": "ok", "usuarios_registrados": len(USERS), "total_mensagens": total}


@app.get("/me")
def me(request: Request):
    user = get_user(request)
    return {"name": user["name"], "email": user["email"], "token": user["token"]}


@app.get("/users")
def list_users(request: Request):
    get_user(request)
    return [{"name": v["name"], "email": v["email"]} for v in USERS.values()]


# ---------------------------------------------------------
# Email — Send
# ---------------------------------------------------------

@app.post("/emails/send", status_code=201)
def send_email(payload: SendEmailRequest, request: Request):
    sender = get_user(request)

    to_list = parse_emails(payload.to)
    cc_list = parse_emails(payload.cc or "")

    if not to_list:
        raise HTTPException(status_code=422, detail="Campo 'to' não pode estar vazio.")

    # Valida todos os destinatários
    all_recipients = to_list + cc_list
    invalid = [e for e in all_recipients if e not in EMAIL_TO_TOKEN]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Destinatário(s) não encontrado(s): {', '.join(invalid)}. O email não pôde ser enviado."
        )

    # Remove o próprio remetente se estiver na lista (silenciosamente)
    to_list = [e for e in to_list if e != sender["email"]]
    cc_list = [e for e in cc_list if e != sender["email"]]

    if not to_list:
        raise HTTPException(status_code=422, detail="Você não pode enviar um email apenas para si mesmo.")

    msg_id    = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        conn.execute(
            """INSERT INTO messages
               (id, from_email, to_emails, cc_emails, subject, body, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (msg_id, sender["email"],
             json.dumps(to_list), json.dumps(cc_list),
             payload.subject, payload.body, timestamp)
        )

    return {
        "status":    "sent",
        "id":        msg_id,
        "from":      sender["email"],
        "to":        to_list,
        "cc":        cc_list,
        "subject":   payload.subject,
        "timestamp": timestamp,
    }


# ---------------------------------------------------------
# Email — Inbox / Sent
# ---------------------------------------------------------

@app.get("/emails/inbox")
def inbox(request: Request):
    user = get_user(request)
    my_email = user["email"]

    with get_db() as conn:
        # Busca todas as mensagens onde o usuário é destinatário (To ou CC)
        rows = conn.execute(
            """SELECT * FROM messages
               WHERE (to_emails LIKE ? OR cc_emails LIKE ?)
               ORDER BY timestamp DESC""",
            (f'%{my_email}%', f'%{my_email}%')
        ).fetchall()

    msgs = [
        row_to_dict(r, my_email)
        for r in rows
        if is_recipient_of(r, my_email) and not has_deleted(r, my_email)
    ]
    return {"email": my_email, "count": len(msgs), "messages": msgs}


@app.get("/emails/sent")
def sent(request: Request):
    user = get_user(request)
    my_email = user["email"]

    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM messages
               WHERE from_email = ? AND deleted_by_sender = 0
               ORDER BY timestamp DESC""",
            (my_email,)
        ).fetchall()

    msgs = [row_to_dict(r, my_email) for r in rows]
    return {"email": my_email, "count": len(msgs), "messages": msgs}


# ---------------------------------------------------------
# Email — Read
# ---------------------------------------------------------

@app.get("/emails/{message_id}")
def get_message(message_id: str, request: Request):
    user = get_user(request)
    my_email = user["email"]

    with get_db() as conn:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Mensagem não encontrada.")

        is_sender    = my_email == row["from_email"]
        is_recipient = is_recipient_of(row, my_email)

        if not is_sender and not is_recipient:
            raise HTTPException(status_code=403, detail="Acesso negado.")

        if is_recipient and has_deleted(row, my_email):
            raise HTTPException(status_code=404, detail="Mensagem não encontrada.")
        if is_sender and row["deleted_by_sender"]:
            raise HTTPException(status_code=404, detail="Mensagem não encontrada.")

        # Marca como lido se for destinatário
        if is_recipient and not row["is_read"]:
            conn.execute("UPDATE messages SET is_read = 1 WHERE id = ?", (message_id,))

    return row_to_dict(row, my_email)


# ---------------------------------------------------------
# Email — Delete
# ---------------------------------------------------------

@app.delete("/emails/{message_id}")
def delete_message(message_id: str, request: Request):
    user = get_user(request)
    my_email = user["email"]

    with get_db() as conn:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Mensagem não encontrada.")

        is_sender    = my_email == row["from_email"]
        is_recipient = is_recipient_of(row, my_email)

        if not is_sender and not is_recipient:
            raise HTTPException(status_code=403, detail="Acesso negado.")

        if is_sender:
            conn.execute("UPDATE messages SET deleted_by_sender = 1 WHERE id = ?", (message_id,))
        else:
            deleted = json.loads(row["deleted_by_recipient"])
            if my_email not in deleted:
                deleted.append(my_email)
            conn.execute(
                "UPDATE messages SET deleted_by_recipient = ? WHERE id = ?",
                (json.dumps(deleted), message_id)
            )

        # Remove fisicamente quando remetente E todos os destinatários deletaram
        row2 = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        if row2:
            all_recipients = json.loads(row2["to_emails"]) + json.loads(row2["cc_emails"])
            deleted_list   = json.loads(row2["deleted_by_recipient"])
            everyone_deleted = (
                row2["deleted_by_sender"] == 1 and
                all(r in deleted_list for r in all_recipients)
            )
            if everyone_deleted:
                conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))

    return {"status": "deleted", "id": message_id}


# ---------------------------------------------------------
# Frontend estático
# ---------------------------------------------------------

_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
