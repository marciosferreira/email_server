import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Union

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from db import EMAIL_TO_TOKEN, get_db, get_user, parse_emails

router = APIRouter(tags=["Email"])


class SendEmailRequest(BaseModel):
    to: Union[str, List[str]]
    cc: Union[str, List[str], None] = ""
    subject: str
    body: str


def _is_recipient_of(msg, email: str) -> bool:
    return email in json.loads(msg["to_emails"]) or email in json.loads(msg["cc_emails"])


def _has_deleted(msg, email: str) -> bool:
    return email in json.loads(msg["deleted_by_recipient"])


def _validate_date_params(data, data_ini, data_fim):
    for nome, val in [("data", data), ("data_ini", data_ini), ("data_fim", data_fim)]:
        if val:
            try:
                datetime.strptime(val, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=422, detail=f"'{nome}' deve ser YYYY-MM-DD.")


def _row_to_dict(msg, my_email: str) -> dict:
    return {
        "id":        msg["id"],
        "from":      msg["from_email"],
        "to":        json.loads(msg["to_emails"]),
        "cc":        json.loads(msg["cc_emails"]),
        "subject":   msg["subject"],
        "body":      msg["body"],
        "timestamp": msg["timestamp"],
        "read":      bool(msg["is_read"]),
    }


@router.post("/emails/send", status_code=201)
def send_email(payload: SendEmailRequest, request: Request):
    sender = get_user(request)

    to_list = parse_emails(payload.to)
    cc_list = parse_emails(payload.cc or "")

    if not to_list:
        raise HTTPException(status_code=422, detail="Campo 'to' não pode estar vazio.")

    invalid = [e for e in to_list + cc_list if e not in EMAIL_TO_TOKEN]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Destinatário(s) não encontrado(s): {', '.join(invalid)}. O email não pôde ser enviado."
        )


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


@router.get("/emails/inbox")
def inbox(
    request:  Request,
    data:     Optional[str] = None,
    data_ini: Optional[str] = None,
    data_fim: Optional[str] = None,
):
    user = get_user(request)
    my_email = user["email"]
    _validate_date_params(data, data_ini, data_fim)

    with get_db() as conn:
        if data:
            rows = conn.execute(
                """SELECT * FROM messages
                   WHERE (to_emails LIKE ? OR cc_emails LIKE ?)
                     AND DATE(timestamp) = ?
                   ORDER BY timestamp DESC""",
                (f'%{my_email}%', f'%{my_email}%', data)
            ).fetchall()
        elif data_ini and data_fim:
            rows = conn.execute(
                """SELECT * FROM messages
                   WHERE (to_emails LIKE ? OR cc_emails LIKE ?)
                     AND DATE(timestamp) BETWEEN ? AND ?
                   ORDER BY timestamp DESC""",
                (f'%{my_email}%', f'%{my_email}%', data_ini, data_fim)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM messages
                   WHERE (to_emails LIKE ? OR cc_emails LIKE ?)
                   ORDER BY timestamp DESC""",
                (f'%{my_email}%', f'%{my_email}%')
            ).fetchall()

    msgs = [
        _row_to_dict(r, my_email)
        for r in rows
        if _is_recipient_of(r, my_email) and not _has_deleted(r, my_email)
    ]
    return {"email": my_email, "count": len(msgs), "messages": msgs}


@router.get("/emails/sent")
def sent(
    request:  Request,
    data:     Optional[str] = None,
    data_ini: Optional[str] = None,
    data_fim: Optional[str] = None,
):
    user = get_user(request)
    my_email = user["email"]
    _validate_date_params(data, data_ini, data_fim)

    with get_db() as conn:
        if data:
            rows = conn.execute(
                """SELECT * FROM messages
                   WHERE from_email = ? AND deleted_by_sender = 0
                     AND DATE(timestamp) = ?
                   ORDER BY timestamp DESC""",
                (my_email, data)
            ).fetchall()
        elif data_ini and data_fim:
            rows = conn.execute(
                """SELECT * FROM messages
                   WHERE from_email = ? AND deleted_by_sender = 0
                     AND DATE(timestamp) BETWEEN ? AND ?
                   ORDER BY timestamp DESC""",
                (my_email, data_ini, data_fim)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM messages
                   WHERE from_email = ? AND deleted_by_sender = 0
                   ORDER BY timestamp DESC""",
                (my_email,)
            ).fetchall()

    return {"email": my_email, "count": len(rows), "messages": [_row_to_dict(r, my_email) for r in rows]}


@router.get("/emails/{message_id}")
def get_message(message_id: str, request: Request):
    user = get_user(request)
    my_email = user["email"]

    with get_db() as conn:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail={
                "erro": "Mensagem não encontrada.",
                "message_id": message_id,
                "dica": "Verifique o id em GET /emails/inbox ou GET /emails/sent.",
            })

        is_sender    = my_email == row["from_email"]
        is_recipient = _is_recipient_of(row, my_email)

        if not is_sender and not is_recipient:
            raise HTTPException(status_code=403, detail={
                "erro": "Acesso negado.",
                "motivo": f"O usuário '{my_email}' não é remetente nem destinatário da mensagem '{message_id}'.",
                "dica": "Você só pode acessar mensagens que enviou ou recebeu.",
            })

        if is_recipient and _has_deleted(row, my_email):
            raise HTTPException(status_code=404, detail={
                "erro": "Mensagem não encontrada.",
                "motivo": f"A mensagem '{message_id}' foi deletada por '{my_email}'.",
            })
        if is_sender and row["deleted_by_sender"]:
            raise HTTPException(status_code=404, detail={
                "erro": "Mensagem não encontrada.",
                "motivo": f"A mensagem '{message_id}' foi deletada pelo remetente.",
            })

        if is_recipient and not row["is_read"]:
            conn.execute("UPDATE messages SET is_read = 1 WHERE id = ?", (message_id,))

    return _row_to_dict(row, my_email)


@router.delete("/emails/{message_id}")
def delete_message(message_id: str, request: Request):
    user = get_user(request)
    my_email = user["email"]

    with get_db() as conn:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail={
                "erro": "Mensagem não encontrada.",
                "message_id": message_id,
                "dica": "Verifique o id em GET /emails/inbox ou GET /emails/sent.",
            })

        is_sender    = my_email == row["from_email"]
        is_recipient = _is_recipient_of(row, my_email)

        if not is_sender and not is_recipient:
            raise HTTPException(status_code=403, detail={
                "erro": "Acesso negado.",
                "motivo": f"O usuário '{my_email}' não é remetente nem destinatário da mensagem '{message_id}'.",
                "dica": "Você só pode deletar mensagens que enviou ou recebeu.",
            })

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

        row2 = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        if row2:
            all_recipients = json.loads(row2["to_emails"]) + json.loads(row2["cc_emails"])
            deleted_list   = json.loads(row2["deleted_by_recipient"])
            if row2["deleted_by_sender"] == 1 and all(r in deleted_list for r in all_recipients):
                conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))

    return {"status": "deleted", "id": message_id}
