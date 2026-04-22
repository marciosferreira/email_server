import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, field_validator, model_validator

from db import get_db, get_user

router = APIRouter(prefix="/agenda", tags=["Agenda"])


class CompromissoCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = ""
    data: str
    hora_inicio: str
    hora_fim: str

    @field_validator("data")
    @classmethod
    def valida_data(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Campo 'data' deve estar no formato YYYY-MM-DD.")
        return v

    @field_validator("hora_inicio", "hora_fim")
    @classmethod
    def valida_hora(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Horários devem estar no formato HH:MM (ex: 09:30).")
        return v

    @model_validator(mode="after")
    def hora_fim_maior(self) -> "CompromissoCreate":
        try:
            inicio = datetime.strptime(self.hora_inicio, "%H:%M")
            fim    = datetime.strptime(self.hora_fim,    "%H:%M")
        except ValueError:
            return self
        if fim <= inicio:
            raise ValueError("'hora_fim' deve ser posterior a 'hora_inicio'.")
        return self


class CompromissoUpdate(BaseModel):
    titulo:      Optional[str] = None
    descricao:   Optional[str] = None
    data:        Optional[str] = None
    hora_inicio: Optional[str] = None
    hora_fim:    Optional[str] = None

    @field_validator("data")
    @classmethod
    def valida_data(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Campo 'data' deve estar no formato YYYY-MM-DD.")
        return v

    @field_validator("hora_inicio", "hora_fim")
    @classmethod
    def valida_hora(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, "%H:%M")
            except ValueError:
                raise ValueError("Horários devem estar no formato HH:MM (ex: 09:30).")
        return v


def _row_to_dict(row) -> dict:
    return {
        "id":          row["id"],
        "titulo":      row["titulo"],
        "descricao":   row["descricao"],
        "data":        row["data"],
        "hora_inicio": row["hora_inicio"],
        "hora_fim":    row["hora_fim"],
        "criado_em":   row["criado_em"],
    }


def _check_overlap(conn, user_email: str, data: str, hora_inicio: str, hora_fim: str, exclude_id: str = None):
    query = """
        SELECT id, titulo, hora_inicio, hora_fim
        FROM compromissos
        WHERE user_email = ?
          AND data       = ?
          AND hora_inicio < ?
          AND hora_fim    > ?
    """
    params = [user_email, data, hora_fim, hora_inicio]
    if exclude_id:
        query += " AND id != ?"
        params.append(exclude_id)

    conflito = conn.execute(query, params).fetchone()
    if conflito:
        raise HTTPException(
            status_code=409,
            detail={
                "erro": "Conflito de horário",
                "mensagem": (
                    f"O horário {hora_inicio}–{hora_fim} conflita com "
                    f"'{conflito['titulo']}' ({conflito['hora_inicio']}–{conflito['hora_fim']})."
                ),
                "conflito_id": conflito["id"],
            },
        )


@router.get("")
def listar_compromissos(
    request:  Request,
    data:     Optional[str] = None,
    data_ini: Optional[str] = None,
    data_fim: Optional[str] = None,
):
    user = get_user(request)

    for nome, val in [("data", data), ("data_ini", data_ini), ("data_fim", data_fim)]:
        if val:
            try:
                datetime.strptime(val, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=422, detail=f"'{nome}' deve ser YYYY-MM-DD.")

    with get_db() as conn:
        if data:
            rows = conn.execute(
                "SELECT * FROM compromissos WHERE user_email=? AND data=? ORDER BY hora_inicio",
                (user["email"], data),
            ).fetchall()
        elif data_ini and data_fim:
            rows = conn.execute(
                """SELECT * FROM compromissos
                   WHERE user_email=? AND data BETWEEN ? AND ?
                   ORDER BY data, hora_inicio""",
                (user["email"], data_ini, data_fim),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM compromissos WHERE user_email=? ORDER BY data, hora_inicio",
                (user["email"],),
            ).fetchall()

    items = [_row_to_dict(r) for r in rows]
    return {"email": user["email"], "count": len(items), "compromissos": items}


@router.post("", status_code=201)
def criar_compromisso(payload: CompromissoCreate, request: Request):
    user = get_user(request)

    with get_db() as conn:
        _check_overlap(conn, user["email"], payload.data, payload.hora_inicio, payload.hora_fim)

        new_id    = str(uuid.uuid4())
        criado_em = datetime.utcnow().isoformat()

        conn.execute(
            """INSERT INTO compromissos
               (id, user_email, titulo, descricao, data, hora_inicio, hora_fim, criado_em)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (new_id, user["email"], payload.titulo, payload.descricao or "",
             payload.data, payload.hora_inicio, payload.hora_fim, criado_em),
        )

    return {
        "status":      "created",
        "id":          new_id,
        "titulo":      payload.titulo,
        "descricao":   payload.descricao,
        "data":        payload.data,
        "hora_inicio": payload.hora_inicio,
        "hora_fim":    payload.hora_fim,
        "criado_em":   criado_em,
    }


@router.get("/{compromisso_id}")
def obter_compromisso(compromisso_id: str, request: Request):
    user = get_user(request)

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM compromissos WHERE id=? AND user_email=?",
            (compromisso_id, user["email"]),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail={
            "erro": "Compromisso não encontrado.",
            "compromisso_id": compromisso_id,
            "dica": "Use GET /agenda para listar os ids disponíveis para o usuário autenticado.",
        })

    return _row_to_dict(row)


@router.put("/{compromisso_id}")
def editar_compromisso(compromisso_id: str, payload: CompromissoUpdate, request: Request):
    user = get_user(request)

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM compromissos WHERE id=? AND user_email=?",
            (compromisso_id, user["email"]),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail={
                "erro": "Compromisso não encontrado.",
                "compromisso_id": compromisso_id,
                "dica": "Use GET /agenda para listar os ids disponíveis para o usuário autenticado.",
            })

        novo_titulo      = payload.titulo      if payload.titulo      is not None else row["titulo"]
        nova_descricao   = payload.descricao   if payload.descricao   is not None else row["descricao"]
        nova_data        = payload.data        if payload.data        is not None else row["data"]
        nova_hora_inicio = payload.hora_inicio if payload.hora_inicio is not None else row["hora_inicio"]
        nova_hora_fim    = payload.hora_fim    if payload.hora_fim    is not None else row["hora_fim"]

        if datetime.strptime(nova_hora_fim, "%H:%M") <= datetime.strptime(nova_hora_inicio, "%H:%M"):
            raise HTTPException(status_code=422, detail={
                "erro": "'hora_fim' deve ser posterior a 'hora_inicio'.",
                "hora_inicio_recebida": nova_hora_inicio,
                "hora_fim_recebida": nova_hora_fim,
            })

        _check_overlap(conn, user["email"], nova_data, nova_hora_inicio, nova_hora_fim,
                       exclude_id=compromisso_id)

        conn.execute(
            """UPDATE compromissos
               SET titulo=?, descricao=?, data=?, hora_inicio=?, hora_fim=?
               WHERE id=?""",
            (novo_titulo, nova_descricao, nova_data, nova_hora_inicio, nova_hora_fim, compromisso_id),
        )

    return {
        "status":      "updated",
        "id":          compromisso_id,
        "titulo":      novo_titulo,
        "descricao":   nova_descricao,
        "data":        nova_data,
        "hora_inicio": nova_hora_inicio,
        "hora_fim":    nova_hora_fim,
    }


@router.delete("/{compromisso_id}")
def deletar_compromisso(compromisso_id: str, request: Request):
    user = get_user(request)

    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM compromissos WHERE id=? AND user_email=?",
            (compromisso_id, user["email"]),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail={
                "erro": "Compromisso não encontrado.",
                "compromisso_id": compromisso_id,
                "dica": "Use GET /agenda para listar os ids disponíveis para o usuário autenticado.",
            })

        conn.execute("DELETE FROM compromissos WHERE id=?", (compromisso_id,))

    return {"status": "deleted", "id": compromisso_id}
