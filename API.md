# API — Mock Email + Agenda Service

Serviço de backend para o curso de Agentes IA. Fornece dois módulos independentes (Email e Agenda) acessíveis via HTTP/REST. Todos os endpoints retornam e consomem JSON.

**Base URL:** `http://localhost:8000`
**Documentação interativa:** `http://localhost:8000/docs`

---

## Autenticação

Todos os endpoints (exceto `/auth/login` e `/health`) exigem o header:

```
Authorization: Bearer <token-ou-email>
```

São aceitas duas formas de credencial:

| Forma | Exemplo |
|---|---|
| Token | `aluno-01` … `aluno-10` |
| E-mail | `aluno01@curso.ia` … `aluno10@curso.ia` |

**Usuários disponíveis:**

| Token | Nome | E-mail |
|---|---|---|
| aluno-01 | Aluno 1 | aluno01@curso.ia |
| aluno-02 | Aluno 2 | aluno02@curso.ia |
| aluno-03 | Aluno 3 | aluno03@curso.ia |
| aluno-04 | Aluno 4 | aluno04@curso.ia |
| aluno-05 | Aluno 5 | aluno05@curso.ia |
| aluno-06 | Aluno 6 | aluno06@curso.ia |
| aluno-07 | Aluno 7 | aluno07@curso.ia |
| aluno-08 | Aluno 8 | aluno08@curso.ia |
| aluno-09 | Aluno 9 | aluno09@curso.ia |
| aluno-10 | Aluno 10 | aluno10@curso.ia |

Senha de todos os usuários: `1234`

---

## Erros comuns de autenticação

**401 — Header ausente**
```json
{
  "erro": "Token de autenticação ausente.",
  "dica": "Inclua o header: Authorization: Bearer <token-ou-email>",
  "exemplos": ["Authorization: Bearer aluno-01", "Authorization: Bearer aluno01@curso.ia"]
}
```

**403 — Credencial inválida**
```json
{
  "erro": "Credencial inválida.",
  "credencial_recebida": "xyz",
  "dica": "Use um token (ex: 'aluno-01') ou email (ex: 'aluno01@curso.ia'). Consulte GET /users para ver os usuários disponíveis."
}
```

---

## Módulo Geral

### POST /auth/login
Autentica um usuário e retorna seu token e e-mail.

**Body:**
```json
{
  "token": "aluno-01",
  "password": "1234"
}
```

**Resposta 200:**
```json
{
  "token": "aluno-01",
  "name": "Aluno 1",
  "email": "aluno01@curso.ia"
}
```

**Erros:**

| Status | Situação |
|---|---|
| 401 | Token não encontrado ou senha incorreta |

---

### GET /health
Verifica o status do serviço. Não requer autenticação.

**Resposta 200:**
```json
{
  "status": "ok",
  "usuarios_registrados": 10,
  "total_mensagens": 42,
  "total_compromissos": 7
}
```

---

### GET /me
Retorna os dados do usuário autenticado.

**Resposta 200:**
```json
{
  "name": "Aluno 1",
  "email": "aluno01@curso.ia",
  "token": "aluno-01"
}
```

---

### GET /users
Lista todos os usuários cadastrados. Útil para descobrir e-mails válidos antes de enviar mensagens.

**Resposta 200:**
```json
[
  { "name": "Aluno 1", "email": "aluno01@curso.ia" },
  { "name": "Aluno 2", "email": "aluno02@curso.ia" }
]
```

---

## Módulo Email

### POST /emails/send
Envia um e-mail para um ou mais destinatários.

**Body:**
```json
{
  "to": "aluno02@curso.ia",
  "cc": "aluno03@curso.ia",
  "subject": "Assunto da mensagem",
  "body": "Corpo da mensagem."
}
```

- `to` — obrigatório. Aceita string única, lista de strings, ou múltiplos e-mails separados por vírgula/ponto-e-vírgula.
- `cc` — opcional. Mesmos formatos aceitos em `to`.
- O remetente é definido pelo token de autenticação. Não é possível enviar apenas para si mesmo.

**Resposta 201:**
```json
{
  "status": "sent",
  "id": "3f2a1b4c-...",
  "from": "aluno01@curso.ia",
  "to": ["aluno02@curso.ia"],
  "cc": ["aluno03@curso.ia"],
  "subject": "Assunto da mensagem",
  "timestamp": "2024-01-15T10:30:00.000000+00:00"
}
```

**Erros:**

| Status | Situação |
|---|---|
| 422 | Campo `to` vazio |
| 422 | Um ou mais destinatários não existem no sistema |
| 422 | Todos os destinatários são o próprio remetente |

---

### GET /emails/inbox
Lista as mensagens recebidas pelo usuário autenticado (To ou CC).

**Query params (todos opcionais):**

| Parâmetro | Formato | Descrição |
|---|---|---|
| `data` | `YYYY-MM-DD` | Filtra por dia exato |
| `data_ini` | `YYYY-MM-DD` | Início do intervalo |
| `data_fim` | `YYYY-MM-DD` | Fim do intervalo (inclusivo) |

> Para filtro por intervalo, informe `data_ini` e `data_fim` juntos.
> Sem parâmetros, retorna todas as mensagens.

**Exemplos:**
```
GET /emails/inbox
GET /emails/inbox?data=2024-01-15
GET /emails/inbox?data_ini=2024-01-01&data_fim=2024-01-31
```

**Resposta 200:**
```json
{
  "email": "aluno02@curso.ia",
  "count": 2,
  "messages": [
    {
      "id": "3f2a1b4c-...",
      "from": "aluno01@curso.ia",
      "to": ["aluno02@curso.ia"],
      "cc": [],
      "subject": "Assunto",
      "body": "Corpo da mensagem.",
      "timestamp": "2024-01-15T10:30:00.000000+00:00",
      "read": false
    }
  ]
}
```

---

### GET /emails/sent
Lista as mensagens enviadas pelo usuário autenticado.

**Query params:** idênticos ao `/emails/inbox`.

**Resposta 200:** mesma estrutura do inbox.

---

### GET /emails/{message_id}
Retorna uma mensagem específica pelo ID. Marca como lida automaticamente se o usuário for destinatário.

**Resposta 200:** objeto de mensagem (mesma estrutura dos itens do inbox).

**Erros:**

| Status | Situação |
|---|---|
| 404 | Mensagem não existe ou foi deletada |
| 403 | Usuário não é remetente nem destinatário |

**Exemplo de erro 404:**
```json
{
  "erro": "Mensagem não encontrada.",
  "message_id": "3f2a1b4c-...",
  "dica": "Verifique o id em GET /emails/inbox ou GET /emails/sent."
}
```

**Exemplo de erro 403:**
```json
{
  "erro": "Acesso negado.",
  "motivo": "O usuário 'aluno03@curso.ia' não é remetente nem destinatário da mensagem '3f2a1b4c-...'.",
  "dica": "Você só pode acessar mensagens que enviou ou recebeu."
}
```

---

### DELETE /emails/{message_id}
Remove uma mensagem. O comportamento é por soft-delete:

- Se o **remetente** deletar: a mensagem some do sent do remetente.
- Se o **destinatário** deletar: a mensagem some do inbox do destinatário.
- A mensagem é removida permanentemente do banco somente quando **todos** (remetente + todos os destinatários) tiverem deletado.

**Resposta 200:**
```json
{
  "status": "deleted",
  "id": "3f2a1b4c-..."
}
```

**Erros:** idem ao `GET /emails/{message_id}`.

---

## Módulo Agenda

Cada usuário tem sua agenda independente. Não é possível ver ou editar compromissos de outro usuário.

### GET /agenda
Lista os compromissos do usuário autenticado.

**Query params (todos opcionais):**

| Parâmetro | Formato | Descrição |
|---|---|---|
| `data` | `YYYY-MM-DD` | Filtra por dia exato |
| `data_ini` | `YYYY-MM-DD` | Início do intervalo |
| `data_fim` | `YYYY-MM-DD` | Fim do intervalo (inclusivo) |

**Exemplos:**
```
GET /agenda
GET /agenda?data=2024-01-15
GET /agenda?data_ini=2024-01-01&data_fim=2024-01-31
```

**Resposta 200:**
```json
{
  "email": "aluno01@curso.ia",
  "count": 1,
  "compromissos": [
    {
      "id": "a1b2c3d4-...",
      "titulo": "Reunião de equipe",
      "descricao": "Revisão do sprint",
      "data": "2024-01-15",
      "hora_inicio": "09:00",
      "hora_fim": "10:00",
      "criado_em": "2024-01-14T18:00:00"
    }
  ]
}
```

---

### POST /agenda
Cria um novo compromisso.

**Body:**
```json
{
  "titulo": "Reunião de equipe",
  "descricao": "Revisão do sprint",
  "data": "2024-01-15",
  "hora_inicio": "09:00",
  "hora_fim": "10:00"
}
```

- `titulo` — obrigatório.
- `descricao` — opcional (padrão: string vazia).
- `data` — obrigatório, formato `YYYY-MM-DD`.
- `hora_inicio` / `hora_fim` — obrigatórios, formato `HH:MM`. `hora_fim` deve ser posterior a `hora_inicio`.
- Não são permitidos compromissos com horários sobrepostos no mesmo dia.

**Resposta 201:**
```json
{
  "status": "created",
  "id": "a1b2c3d4-...",
  "titulo": "Reunião de equipe",
  "descricao": "Revisão do sprint",
  "data": "2024-01-15",
  "hora_inicio": "09:00",
  "hora_fim": "10:00",
  "criado_em": "2024-01-14T18:00:00"
}
```

**Erros:**

| Status | Situação |
|---|---|
| 422 | Formato de data ou hora inválido |
| 422 | `hora_fim` não é posterior a `hora_inicio` |
| 409 | Conflito de horário com outro compromisso existente |

**Exemplo de erro 409:**
```json
{
  "erro": "Conflito de horário",
  "mensagem": "O horário 09:30–10:30 conflita com 'Reunião de equipe' (09:00–10:00).",
  "conflito_id": "a1b2c3d4-..."
}
```

---

### GET /agenda/{compromisso_id}
Retorna um compromisso específico pelo ID.

**Resposta 200:** objeto de compromisso (mesma estrutura dos itens do GET /agenda).

**Erros:**

| Status | Situação |
|---|---|
| 404 | Compromisso não existe ou pertence a outro usuário |

**Exemplo de erro 404:**
```json
{
  "erro": "Compromisso não encontrado.",
  "compromisso_id": "a1b2c3d4-...",
  "dica": "Use GET /agenda para listar os ids disponíveis para o usuário autenticado."
}
```

---

### PUT /agenda/{compromisso_id}
Atualiza um compromisso existente. Apenas os campos enviados são alterados (comportamento de PATCH).

**Body (todos os campos são opcionais):**
```json
{
  "titulo": "Novo título",
  "descricao": "Nova descrição",
  "data": "2024-01-16",
  "hora_inicio": "10:00",
  "hora_fim": "11:00"
}
```

**Resposta 200:**
```json
{
  "status": "updated",
  "id": "a1b2c3d4-...",
  "titulo": "Novo título",
  "descricao": "Nova descrição",
  "data": "2024-01-16",
  "hora_inicio": "10:00",
  "hora_fim": "11:00"
}
```

**Erros:** idem ao `POST /agenda`, mais o 404 do `GET /agenda/{id}`.

---

### DELETE /agenda/{compromisso_id}
Remove um compromisso permanentemente.

**Resposta 200:**
```json
{
  "status": "deleted",
  "id": "a1b2c3d4-..."
}
```

**Erros:**

| Status | Situação |
|---|---|
| 404 | Compromisso não existe ou pertence a outro usuário |

---

## Resumo dos endpoints

| Método | Endpoint | Módulo | Descrição |
|---|---|---|---|
| POST | /auth/login | Geral | Autentica e retorna token |
| GET | /health | Geral | Status do serviço |
| GET | /me | Geral | Dados do usuário autenticado |
| GET | /users | Geral | Lista todos os usuários |
| POST | /emails/send | Email | Envia um e-mail |
| GET | /emails/inbox | Email | Lista mensagens recebidas |
| GET | /emails/sent | Email | Lista mensagens enviadas |
| GET | /emails/{id} | Email | Lê uma mensagem |
| DELETE | /emails/{id} | Email | Deleta uma mensagem |
| GET | /agenda | Agenda | Lista compromissos |
| POST | /agenda | Agenda | Cria um compromisso |
| GET | /agenda/{id} | Agenda | Lê um compromisso |
| PUT | /agenda/{id} | Agenda | Atualiza um compromisso |
| DELETE | /agenda/{id} | Agenda | Deleta um compromisso |
