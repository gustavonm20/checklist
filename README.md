# Checklist

Aplicação web para organizar múltiplos checklists, tarefas e datas de planejamento.

## Funcionalidades

- Cadastro e login de usuários;
- Senhas armazenadas com hash;
- Dados separados por usuário;
- Criação de vários checklists;
- Edição, arquivamento e exclusão de checklists;
- Cores diferentes para cada tema;
- Criação, edição, conclusão e exclusão de tarefas;
- Data planejada para cada checklist;
- Página de calendário;
- Indicadores de progresso;
- Banco SQLite criado automaticamente;
- Interface responsiva, colorida e sem degradês.

## Tecnologias

- Python
- Flask
- Flask-SQLAlchemy
- SQLite
- HTML, CSS e JavaScript

## Como executar

```bash
python -m venv .venv
```

No Windows:

```bash
.venv\Scripts\activate
```

Instale as dependências e inicie:

```bash
pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000`.
