from datetime import datetime, timezone
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify
)
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import supabase_admin

contabilidade_externa_bp = Blueprint(
    "contabilidade_externa",
    __name__,
    url_prefix="/portal-contabilidade",
    template_folder="templates",
    static_folder="static",
    static_url_path="/portal-contabilidade/static"
)



def _is_password_hash(value: str) -> bool:
    """Verifica heurísticamente se a string já está no formato de hash suportado."""
    if not value or not isinstance(value, str):
        return False
    return value.startswith("pbkdf2:") or value.startswith("scrypt:")


def _formatar_evento(item: dict) -> dict:
    """Normaliza o payload do histórico para consumo no portal externo."""
    if not item:
        return {}

    evento = {key: value for key, value in item.items() if key != "senha_hash"}

    colaborador_info = (item.get("colaborador") or {})
    cargo_info = item.get("cargo") or {}
    departamento_info = item.get("departamento") or {}
    empresa_info = item.get("empresa") or {}

    evento["colaborador"] = {
        "id": colaborador_info.get("id"),
        "nome_completo": colaborador_info.get("nome_completo"),
        "cpf": colaborador_info.get("cpf"),
        "matricula": colaborador_info.get("matricula"),
        "email_corporativo": colaborador_info.get("email_corporativo"),
        "data_nascimento": colaborador_info.get("data_nascimento"),
        "pis_pasep": colaborador_info.get("pis_pasep"),
    }

    evento["cargo"] = cargo_info
    evento["departamento"] = departamento_info
    evento["empresa"] = empresa_info

    evento["cargo_nome"] = cargo_info.get("nome_cargo")
    evento["departamento_nome"] = departamento_info.get("nome_departamento")
    evento["empresa_nome"] = empresa_info.get("razao_social")

    evento["dados_adicionais"] = item.get("dados_adicionais_jsonb") or {}
    evento.pop("dados_adicionais_jsonb", None)

    evento["salario_mensal"] = evento.get("salario_mensal")
    evento["status_contabilidade"] = evento.get("status_contabilidade") or "Pendente"

    return evento


def _contabilidade_autenticada() -> bool:
    """Check if the current session belongs to a logged in accounting user."""
    return session.get("contabilidade_autenticada") is True


def _coletar_pendencias():
    """Load pending events for the accounting portal."""
    response = supabase_admin.table("rh_historico_colaborador") \
        .select(
            (
                "*, "
                "colaborador:rh_colaboradores!rh_historico_colaborador_colaborador_id_fkey("
                "id, nome_completo, cpf, matricula, email_corporativo, data_nascimento, pis_pasep), "
                "cargo:rh_cargos(nome_cargo), "
                "departamento:rh_departamentos(nome_departamento), "
                "empresa:rh_empresas(razao_social)"
            )
        ) \
        .eq("status_contabilidade", "Pendente") \
        .order("data_evento", desc=True) \
        .execute()

    registros = response.data or []
    return [_formatar_evento(item) for item in registros]


@contabilidade_externa_bp.route("/")
def portal_home():
    """Redirect root access to login page."""
    if _contabilidade_autenticada():
        return redirect(url_for("contabilidade_externa.pendencias"))
    return redirect(url_for("contabilidade_externa.login"))


@contabilidade_externa_bp.route("/login", methods=["GET", "POST"])
def login():
    """Render and process the external accounting login screen."""
    if request.method == "POST":
        nome_usuario = (request.form.get("nome_usuario") or "").strip()
        senha = request.form.get("senha") or ""

        if not nome_usuario or not senha:
            flash("Informe usuário e senha.", "error")
            return render_template("contabilidade_externa/login_contabilidade.html", nome_usuario=nome_usuario)

        try:
            response = supabase_admin.table("rh_acesso_contabilidade") \
                .select("id, nome_usuario, senha_hash, descricao, is_active") \
                .eq("nome_usuario", nome_usuario) \
                .eq("is_active", True) \
                .single() \
                .execute()
        except Exception as exc:
            print(f"[CONTABILIDADE] Erro ao buscar usuário {nome_usuario}: {exc}")
            response = None

        user_data = response.data if response and response.data else None
        if not user_data:
            flash("Usuário ou senha inválidos.", "error")
            return render_template("contabilidade_externa/login_contabilidade.html", nome_usuario=nome_usuario)

        senha_hash = user_data.get("senha_hash", "")
        senha_valida = False

        if _is_password_hash(senha_hash):
            senha_valida = check_password_hash(senha_hash, senha)
        else:
            senha_valida = senha_hash == senha

        if not senha_valida:
            flash("Usuário ou senha inválidos.", "error")
            return render_template("contabilidade_externa/login_contabilidade.html", nome_usuario=nome_usuario)

        # Atualiza hash legado caso necessário
        if not _is_password_hash(senha_hash):
            try:
                supabase_admin.table("rh_acesso_contabilidade") \
                    .update({"senha_hash": generate_password_hash(senha)}) \
                    .eq("id", user_data.get("id")) \
                    .execute()
            except Exception as exc:
                print(f"[CONTABILIDADE] Falha ao atualizar hash legado para usuário {nome_usuario}: {exc}")

        session["contabilidade_autenticada"] = True
        session["contabilidade_nome"] = user_data.get("nome_usuario")
        session["contabilidade_usuario_id"] = user_data.get("id")
        session["contabilidade_login_at"] = datetime.now(timezone.utc).isoformat()
        session.permanent = True
        session.modified = True

        return redirect(url_for("contabilidade_externa.pendencias"))

    return render_template("contabilidade_externa/login_contabilidade.html")


@contabilidade_externa_bp.route("/logout")
def logout():
    """Clear accounting session keys and redirect to login."""
    session.pop("contabilidade_autenticada", None)
    session.pop("contabilidade_nome", None)
    session.pop("contabilidade_usuario_id", None)
    session.pop("contabilidade_login_at", None)
    session.modified = True
    flash("Sessão encerrada com sucesso.", "info")
    return redirect(url_for("contabilidade_externa.login"))


@contabilidade_externa_bp.route("/pendencias")
def pendencias():
    """List pending HR events awaiting accounting confirmation."""
    if not _contabilidade_autenticada():
        return redirect(url_for("contabilidade_externa.login"))

    try:
        pendencias_data = _coletar_pendencias()
    except Exception as exc:
        print(f"[CONTABILIDADE] Erro ao carregar pendências: {exc}")
        pendencias_data = []
        flash("Não foi possível carregar as pendências.", "error")

    tipos_evento = sorted({item.get("tipo_evento") for item in pendencias_data if item.get("tipo_evento")})

    return render_template(
        "contabilidade_externa/portal_contabilidade.html",
        pendencias=pendencias_data,
        usuario=session.get("contabilidade_nome"),
        tipos_evento=tipos_evento
    )


@contabilidade_externa_bp.route("/api/eventos/<evento_id>")
def obter_evento(evento_id):
    """Provide event details in JSON format for the modal."""
    if not _contabilidade_autenticada():
        return jsonify({"success": False, "message": "Sessão expirada"}), 401

    try:
        response = supabase_admin.table("rh_historico_colaborador") \
            .select(
                (
                    "*, "
                    "colaborador:rh_colaboradores!rh_historico_colaborador_colaborador_id_fkey("
                    "id, nome_completo, cpf, matricula, email_corporativo, data_nascimento, pis_pasep), "
                    "cargo:rh_cargos(nome_cargo), "
                    "departamento:rh_departamentos(nome_departamento), "
                    "empresa:rh_empresas(razao_social)"
                )
            ) \
            .eq("id", evento_id) \
            .single() \
            .execute()
    except Exception as exc:
        print(f"[CONTABILIDADE] Erro ao buscar evento {evento_id}: {exc}")
        return jsonify({"success": False, "message": "Evento não encontrado"}), 404

    if not response.data:
        return jsonify({"success": False, "message": "Evento não encontrado"}), 404

    payload = _formatar_evento(response.data)
    return jsonify({"success": True, "data": payload})


@contabilidade_externa_bp.route("/api/eventos/<evento_id>/concluir", methods=["POST"])
def concluir_evento(evento_id):
    """Mark a pending event as concluded by accounting."""
    if not _contabilidade_autenticada():
        return jsonify({"success": False, "message": "Sessão expirada"}), 401

    payload = request.get_json(silent=True) or {}
    observacao = (payload.get("observacao") or "").strip()

    try:
        evento_response = supabase_admin.table("rh_historico_colaborador") \
            .select("status_contabilidade, obs_contabilidade") \
            .eq("id", evento_id) \
            .single() \
            .execute()
    except Exception as exc:
        print(f"[CONTABILIDADE] Erro ao validar evento {evento_id}: {exc}")
        return jsonify({"success": False, "message": "Evento não encontrado"}), 404

    dados_existentes = evento_response.data if evento_response and evento_response.data else None
    if not dados_existentes:
        return jsonify({"success": False, "message": "Evento não encontrado"}), 404

    if (dados_existentes.get("status_contabilidade") or "").lower() == "concluído".lower():
        return jsonify({"success": False, "message": "Este evento já foi concluído."}), 400

    usuario_nome = session.get("contabilidade_nome", "Contabilidade")
    timestamp = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")

    comentarios = []
    if dados_existentes.get("obs_contabilidade"):
        comentarios.append(dados_existentes["obs_contabilidade"])
    if observacao:
        comentarios.append(observacao)
    comentarios.append(f"Baixado por: {usuario_nome} em {timestamp}")

    update_payload = {
        "status_contabilidade": "Concluído",
        "data_contabilidade_check": datetime.now(timezone.utc).isoformat(),
        "obs_contabilidade": "\n".join(comentarios)
    }

    try:
        supabase_admin.table("rh_historico_colaborador") \
            .update(update_payload) \
            .eq("id", evento_id) \
            .execute()
    except Exception as exc:
        print(f"[CONTABILIDADE] Erro ao atualizar evento {evento_id}: {exc}")
        return jsonify({"success": False, "message": "Não foi possível concluir o evento."}), 500

    return jsonify({"success": True, "message": "Evento marcado como concluído."})
