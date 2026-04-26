import os
import re
import sqlite3
from contextlib import contextmanager
from typing import List

from fastapi import HTTPException, Request

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
    "aluno-11": {"name": "Aluno 11",  "email": "aluno11@curso.ia", "password": "1234"},
    "aluno-12": {"name": "Aluno 12",  "email": "aluno12@curso.ia", "password": "1234"},
    "aluno-13": {"name": "Aluno 13",  "email": "aluno13@curso.ia", "password": "1234"},
    "aluno-14": {"name": "Aluno 14",  "email": "aluno14@curso.ia", "password": "1234"},
    "aluno-15": {"name": "Aluno 15",  "email": "aluno15@curso.ia", "password": "1234"},
    "aluno-16": {"name": "Aluno 16",  "email": "aluno16@curso.ia", "password": "1234"},
    "aluno-17": {"name": "Aluno 17",  "email": "aluno17@curso.ia", "password": "1234"},
    "aluno-18": {"name": "Aluno 18",  "email": "aluno18@curso.ia", "password": "1234"},
    "aluno-19": {"name": "Aluno 19",  "email": "aluno19@curso.ia", "password": "1234"},
    "aluno-20": {"name": "Aluno 20", "email": "aluno20@curso.ia", "password": "1234"},
}


EMAIL_TO_TOKEN = {v["email"]: k for k, v in USERS.items()}
DB_PATH = os.environ.get("DB_PATH", "email.db")


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
                to_emails            TEXT NOT NULL,
                cc_emails            TEXT NOT NULL DEFAULT '[]',
                subject              TEXT NOT NULL,
                body                 TEXT NOT NULL,
                timestamp            TEXT NOT NULL,
                is_read              INTEGER NOT NULL DEFAULT 0,
                deleted_by_sender    INTEGER NOT NULL DEFAULT 0,
                deleted_by_recipient TEXT NOT NULL DEFAULT '[]'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compromissos (
                id          TEXT PRIMARY KEY,
                user_email  TEXT NOT NULL,
                titulo      TEXT NOT NULL,
                descricao   TEXT NOT NULL DEFAULT '',
                data        TEXT NOT NULL,
                hora_inicio TEXT NOT NULL,
                hora_fim    TEXT NOT NULL,
                criado_em   TEXT NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_comp_user_data ON compromissos (user_email, data)"
        )


def get_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={
            "erro": "Token de autenticação ausente.",
            "dica": "Inclua o header: Authorization: Bearer <token-ou-email>",
            "exemplos": ["Authorization: Bearer aluno-01", "Authorization: Bearer aluno01@curso.ia"],
        })
    credential = auth.removeprefix("Bearer ").strip()
    if credential in USERS:
        token = credential
    elif credential in EMAIL_TO_TOKEN:
        token = EMAIL_TO_TOKEN[credential]
    else:
        raise HTTPException(status_code=403, detail={
            "erro": "Credencial inválida.",
            "credencial_recebida": credential,
            "dica": "Use um token (ex: 'aluno-01') ou email (ex: 'aluno01@curso.ia'). Consulte GET /users para ver os usuários disponíveis.",
        })
    return {"token": token, **USERS[token]}


def parse_emails(raw) -> List[str]:
    if isinstance(raw, list):
        return [e.strip().lower() for e in raw if e.strip()]
    parts = re.split(r"[,;]", raw or "")
    return [e.strip().lower() for e in parts if e.strip()]
