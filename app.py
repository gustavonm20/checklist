from __future__ import annotations

import os
from datetime import date, datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "checklist-local-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///checklist.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    checklists = db.relationship("Checklist", backref="usuario", cascade="all, delete-orphan", lazy=True)


class Checklist(db.Model):
    __tablename__ = "checklists"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(160), nullable=False)
    descricao = db.Column(db.String(500), default="")
    cor = db.Column(db.String(20), default="azul")
    data_planejada = db.Column(db.Date, nullable=True, index=True)
    arquivado = db.Column(db.Boolean, default=False, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    tarefas = db.relationship("Tarefa", backref="checklist", cascade="all, delete-orphan", lazy=True, order_by="Tarefa.ordem")

    @property
    def total(self) -> int:
        return len(self.tarefas)

    @property
    def concluidas(self) -> int:
        return sum(1 for tarefa in self.tarefas if tarefa.concluida)

    @property
    def progresso(self) -> int:
        return round((self.concluidas / self.total) * 100) if self.total else 0


class Tarefa(db.Model):
    __tablename__ = "tarefas"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(240), nullable=False)
    observacao = db.Column(db.String(500), default="")
    concluida = db.Column(db.Boolean, default=False, nullable=False)
    ordem = db.Column(db.Integer, default=0, nullable=False)
    criada_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    checklist_id = db.Column(db.Integer, db.ForeignKey("checklists.id"), nullable=False, index=True)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Entre na sua conta para continuar.", "aviso")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def usuario_atual() -> Usuario | None:
    usuario_id = session.get("usuario_id")
    return db.session.get(Usuario, usuario_id) if usuario_id else None


def checklist_do_usuario(checklist_id: int) -> Checklist | None:
    return Checklist.query.filter_by(id=checklist_id, usuario_id=session.get("usuario_id")).first()


@app.context_processor
def inject_globals():
    return {"usuario_atual": usuario_atual(), "hoje": date.today()}


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        if len(nome) < 2 or "@" not in email or len(senha) < 6:
            flash("Preencha os dados corretamente. A senha precisa ter ao menos 6 caracteres.", "erro")
            return render_template("cadastro.html")
        if Usuario.query.filter_by(email=email).first():
            flash("Esse e-mail já está cadastrado.", "erro")
            return render_template("cadastro.html")
        usuario = Usuario(nome=nome, email=email, senha_hash=generate_password_hash(senha))
        db.session.add(usuario)
        db.session.commit()
        flash("Conta criada. Agora você já pode entrar.", "sucesso")
        return redirect(url_for("login"))
    return render_template("cadastro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario or not check_password_hash(usuario.senha_hash, senha):
            flash("E-mail ou senha incorretos.", "erro")
            return render_template("login.html")
        session.clear()
        session["usuario_id"] = usuario.id
        return redirect(url_for("painel"))
    return render_template("login.html")


@app.route("/sair")
def sair():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def painel():
    filtro = request.args.get("filtro", "ativos")
    query = Checklist.query.filter_by(usuario_id=session["usuario_id"])
    if filtro == "concluidos":
        checklists = [item for item in query.order_by(Checklist.criado_em.desc()).all() if item.total and item.concluidas == item.total]
    elif filtro == "arquivados":
        checklists = query.filter_by(arquivado=True).order_by(Checklist.criado_em.desc()).all()
    else:
        checklists = query.filter_by(arquivado=False).order_by(Checklist.data_planejada.is_(None), Checklist.data_planejada, Checklist.criado_em.desc()).all()
    total_tarefas = sum(item.total for item in query.all())
    total_concluidas = sum(item.concluidas for item in query.all())
    proximos = query.filter(Checklist.data_planejada.isnot(None), Checklist.data_planejada >= date.today(), Checklist.arquivado.is_(False)).order_by(Checklist.data_planejada).limit(5).all()
    return render_template("painel.html", checklists=checklists, filtro=filtro, total_tarefas=total_tarefas, total_concluidas=total_concluidas, proximos=proximos)


@app.route("/checklists/novo", methods=["GET", "POST"])
@login_required
def novo_checklist():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        cor = request.form.get("cor", "azul")
        data_texto = request.form.get("data_planejada", "").strip()
        if not titulo:
            flash("Dê um nome ao checklist.", "erro")
            return render_template("checklist_form.html", checklist=None)
        data_planejada = datetime.strptime(data_texto, "%Y-%m-%d").date() if data_texto else None
        checklist = Checklist(titulo=titulo, descricao=descricao, cor=cor, data_planejada=data_planejada, usuario_id=session["usuario_id"])
        db.session.add(checklist)
        db.session.commit()
        flash("Checklist criado.", "sucesso")
        return redirect(url_for("ver_checklist", checklist_id=checklist.id))
    return render_template("checklist_form.html", checklist=None)


@app.route("/checklists/<int:checklist_id>")
@login_required
def ver_checklist(checklist_id):
    checklist = checklist_do_usuario(checklist_id)
    if not checklist:
        flash("Checklist não encontrado.", "erro")
        return redirect(url_for("painel"))
    return render_template("checklist.html", checklist=checklist)


@app.route("/checklists/<int:checklist_id>/editar", methods=["GET", "POST"])
@login_required
def editar_checklist(checklist_id):
    checklist = checklist_do_usuario(checklist_id)
    if not checklist:
        return redirect(url_for("painel"))
    if request.method == "POST":
        checklist.titulo = request.form.get("titulo", "").strip() or checklist.titulo
        checklist.descricao = request.form.get("descricao", "").strip()
        checklist.cor = request.form.get("cor", "azul")
        data_texto = request.form.get("data_planejada", "").strip()
        checklist.data_planejada = datetime.strptime(data_texto, "%Y-%m-%d").date() if data_texto else None
        db.session.commit()
        flash("Checklist atualizado.", "sucesso")
        return redirect(url_for("ver_checklist", checklist_id=checklist.id))
    return render_template("checklist_form.html", checklist=checklist)


@app.post("/checklists/<int:checklist_id>/excluir")
@login_required
def excluir_checklist(checklist_id):
    checklist = checklist_do_usuario(checklist_id)
    if checklist:
        db.session.delete(checklist)
        db.session.commit()
        flash("Checklist excluído.", "sucesso")
    return redirect(url_for("painel"))


@app.post("/checklists/<int:checklist_id>/arquivar")
@login_required
def arquivar_checklist(checklist_id):
    checklist = checklist_do_usuario(checklist_id)
    if checklist:
        checklist.arquivado = not checklist.arquivado
        db.session.commit()
    return redirect(request.referrer or url_for("painel"))


@app.post("/checklists/<int:checklist_id>/tarefas")
@login_required
def nova_tarefa(checklist_id):
    checklist = checklist_do_usuario(checklist_id)
    titulo = request.form.get("titulo", "").strip()
    observacao = request.form.get("observacao", "").strip()
    if checklist and titulo:
        proxima_ordem = max([tarefa.ordem for tarefa in checklist.tarefas], default=-1) + 1
        db.session.add(Tarefa(titulo=titulo, observacao=observacao, ordem=proxima_ordem, checklist_id=checklist.id))
        db.session.commit()
    return redirect(url_for("ver_checklist", checklist_id=checklist_id))


@app.post("/tarefas/<int:tarefa_id>/alternar")
@login_required
def alternar_tarefa(tarefa_id):
    tarefa = Tarefa.query.join(Checklist).filter(Tarefa.id == tarefa_id, Checklist.usuario_id == session["usuario_id"]).first()
    if tarefa:
        tarefa.concluida = not tarefa.concluida
        db.session.commit()
        return {"ok": True, "concluida": tarefa.concluida, "progresso": tarefa.checklist.progresso}
    return {"ok": False}, 404


@app.post("/tarefas/<int:tarefa_id>/editar")
@login_required
def editar_tarefa(tarefa_id):
    tarefa = Tarefa.query.join(Checklist).filter(Tarefa.id == tarefa_id, Checklist.usuario_id == session["usuario_id"]).first()
    if tarefa:
        tarefa.titulo = request.form.get("titulo", "").strip() or tarefa.titulo
        tarefa.observacao = request.form.get("observacao", "").strip()
        db.session.commit()
    return redirect(url_for("ver_checklist", checklist_id=tarefa.checklist_id if tarefa else 0))


@app.post("/tarefas/<int:tarefa_id>/excluir")
@login_required
def excluir_tarefa(tarefa_id):
    tarefa = Tarefa.query.join(Checklist).filter(Tarefa.id == tarefa_id, Checklist.usuario_id == session["usuario_id"]).first()
    checklist_id = tarefa.checklist_id if tarefa else None
    if tarefa:
        db.session.delete(tarefa)
        db.session.commit()
    return redirect(url_for("ver_checklist", checklist_id=checklist_id) if checklist_id else url_for("painel"))


@app.route("/calendario")
@login_required
def calendario():
    itens = Checklist.query.filter_by(usuario_id=session["usuario_id"], arquivado=False).filter(Checklist.data_planejada.isnot(None)).order_by(Checklist.data_planejada).all()
    agrupados: dict[str, list[Checklist]] = {}
    for item in itens:
        chave = item.data_planejada.strftime("%Y-%m")
        agrupados.setdefault(chave, []).append(item)
    return render_template("calendario.html", agrupados=agrupados)


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
