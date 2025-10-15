import json
import logging
import os
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, render_template, request, session

from extensions import supabase_admin
from routes.auth import login_required, role_required
from services.data_cache import data_cache


def _get_exchange_rates_safe() -> Dict[str, Optional[float]]:
    try:
        from modules.importacoes.dashboards.resumido.routes import (  # pylint: disable=import-outside-toplevel
            get_exchange_rates,
        )

        rates = get_exchange_rates()
        if isinstance(rates, dict):
            return {
                "dolar": rates.get("dolar"),
                "euro": rates.get("euro"),
            }
    except Exception as exc:  # pragma: no cover - resiliente a falhas externas
        logger.warning("[DASH MAPA] Falha ao obter câmbio PTAX: %s", exc)
    return {"dolar": None, "euro": None}

logger = logging.getLogger(__name__)


dashboard_interno_mapa_bp = Blueprint(
    "dashboard_interno_mapa",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/dashboard-interno-mapa/static",
    url_prefix="/dashboard-interno-mapa",
)

CACHE_DATA_TYPE = "dashboard_interno_mapa_view"
SESSION_CACHE_KEY = "dashboard_interno_mapa_processos"


def _is_api_bypass() -> bool:
    api_key = os.getenv("API_BYPASS_KEY")
    return bool(api_key and request.headers.get("X-API-Key") == api_key)


def _apply_auth_decorators(func):
    """Aplica login + role guard quando não estiver usando bypass."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if _is_api_bypass():
            return func(*args, **kwargs)

        guarded = role_required(["admin", "interno_unique"])(login_required(func))
        return guarded(*args, **kwargs)

    return wrapper


@dashboard_interno_mapa_bp.route("/", methods=["GET"])
@login_required
@role_required(["admin", "interno_unique"])
def index():
    """Renderiza a tela do dashboard interno baseado em mapa."""
    return render_template(
        "dashboard_interno_mapa/dashboard_interno_mapa.html",
        user=session.get("user", {}),
    )


def _parse_br_date(value: str) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _safe_float(value):
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return float(value)
        cleaned = str(value).replace(".", "").replace(",", ".")
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _safe_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None


def _parse_pais(pais_raw: str) -> Dict[str, Optional[str]]:
    if not pais_raw or not isinstance(pais_raw, str):
        return {"codigo_numerico": None, "codigo_iso": None, "nome": None}

    parts = [part.strip() for part in pais_raw.split("-") if part.strip()]
    if len(parts) >= 3:
        codigo_numerico = parts[0]
        codigo_iso = parts[1]
        nome = "-".join(parts[2:]).strip()
        return {
            "codigo_numerico": codigo_numerico,
            "codigo_iso": codigo_iso,
            "nome": nome,
        }

    return {"codigo_numerico": None, "codigo_iso": None, "nome": pais_raw.strip()}


def _normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    pais_info = _parse_pais(record.get("pais_procedencia"))

    despesas_raw = record.get("despesas_processo")
    if isinstance(despesas_raw, str):
        try:
            despesas = json.loads(despesas_raw)
        except json.JSONDecodeError:
            despesas = []
    elif isinstance(despesas_raw, list):
        despesas = despesas_raw
    else:
        despesas = []

    return {
        "id": record.get("id"),
        "ref_unique": record.get("ref_unique"),
        "ref_importador": record.get("ref_importador"),
        "cnpj_importador": record.get("cnpj_importador"),
        "importador": record.get("importador"),
        "modal": (record.get("modal") or "").strip() or None,
        "container": record.get("container"),
        "data_embarque": _parse_br_date(record.get("data_embarque")),
        "data_chegada": _parse_br_date(record.get("data_chegada")),
        "transit_time_real": _safe_int(record.get("transit_time_real")),
        "pais_procedencia": record.get("pais_procedencia"),
        "pais_nome": pais_info.get("nome"),
        "pais_codigo": pais_info.get("codigo_iso"),
        "urf_despacho": record.get("urf_despacho"),
        "exportador_fornecedor": record.get("exportador_fornecedor"),
        "numero_di": record.get("numero_di"),
        "data_registro": _parse_br_date(record.get("data_registro")),
        "canal": (record.get("canal") or "").strip() or None,
        "peso_bruto": _safe_float(record.get("peso_bruto")),
        "data_desembaraco": _parse_br_date(record.get("data_desembaraco")),
        "mercadoria": record.get("mercadoria"),
        "data_abertura": _parse_br_date(record.get("data_abertura")),
        "data_fechamento": _parse_br_date(record.get("data_fechamento")),
        "status_sistema": record.get("status_sistema"),
        "status_timeline": record.get("status_timeline"),
        "url_bandeira": record.get("url_bandeira"),
        "despesas_processo": despesas,
    }


def _load_processes(
    user_id: Optional[str],
    user_role: Optional[str],
    user_companies: Optional[List[str]],
    use_session: bool,
):
    cached_session = session.get(SESSION_CACHE_KEY) if use_session else None
    if cached_session:
        logger.info("[DASH MAPA] Cache de sessão encontrado (%s registros)", len(cached_session))
        return cached_session

    cached_service = None
    if user_id:
        cached_service = data_cache.get_cache(user_id, CACHE_DATA_TYPE)
        if cached_service:
            logger.info("[DASH MAPA] Cache do serviço encontrado (%s registros)", len(cached_service))
            if use_session:
                session[SESSION_CACHE_KEY] = cached_service
            return cached_service

    logger.info("[DASH MAPA] Buscando dados no Supabase - role=%s, companies=%s", user_role, user_companies)
    try:
        query = supabase_admin.table("vw_importacoes_6_meses_abertos_dash").select(
            "id, ref_unique, ref_importador, cnpj_importador, importador, modal, container, "
            "data_embarque, data_chegada, transit_time_real, pais_procedencia, urf_despacho, "
            "exportador_fornecedor, numero_di, data_registro, canal, peso_bruto, data_desembaraco, "
            "mercadoria, data_abertura, data_fechamento, status_sistema, status_timeline, url_bandeira, "
            "despesas_processo"
        )

        if user_role == "cliente_unique":
            if not user_companies:
                logger.info("[DASH MAPA] Cliente sem empresas vinculadas")
                return []
            logger.info("[DASH MAPA] Aplicando filtro de empresas para cliente: %s", user_companies)
            query = query.in_("cnpj_importador", user_companies)
        elif user_role == "interno_unique" and user_companies:
            logger.info("[DASH MAPA] Aplicando filtro de empresas para interno: %s", user_companies)
            query = query.in_("cnpj_importador", user_companies)
        else:
            logger.info("[DASH MAPA] SEM filtro de empresas (acesso total)")

        logger.info("[DASH MAPA] Executando query no Supabase...")
        response = query.order("data_abertura", desc=True).limit(3000).execute()
        records = response.data or []
        logger.info("[DASH MAPA] Query retornou %s registros brutos", len(records))
        
        if records:
            logger.info("[DASH MAPA] Exemplo de registro: %s", records[0])
        
        normalized = [_normalize_record(item) for item in records]
        logger.info("[DASH MAPA] %s registros normalizados", len(normalized))

        if use_session:
            session[SESSION_CACHE_KEY] = normalized
        if user_id:
            data_cache.set_cache(user_id, CACHE_DATA_TYPE, normalized)

        return normalized
    except Exception as exc:  # pragma: no cover - proteção extra
        logger.error("[DASH MAPA] Erro ao carregar dados: %s", exc, exc_info=True)
        return []


def _load_meta(current_year: int, current_month: int) -> Dict[str, Any]:
    meta_map: dict[str, int] = {}
    try:
        response = supabase_admin.table("fin_metas_projecoes").select("ano, mes, meta, tipo").eq(
            "tipo", "operacional"
        ).execute()
        for row in response.data or []:
            ano = row.get("ano")
            mes = row.get("mes")
            meta_value = _safe_int(row.get("meta")) or 0
            if not ano or not mes:
                continue
            meta_map[f"{ano}-{str(mes).zfill(2)}"] = meta_value
    except Exception as exc:  # pragma: no cover
        logger.error("[DASH MAPA] Erro ao carregar metas: %s", exc)

    current_key = f"{current_year}-{str(current_month).zfill(2)}"
    return {
        "current_meta": meta_map.get(current_key) or 0,
        "items": meta_map,
    }


def _build_user_context() -> Dict[str, Any]:
    if _is_api_bypass():
        logger.debug("[DASH MAPA] Requisição em modo bypass")
        return {
            "user_id": "dashboard_mapa_bypass",
            "user_role": "admin",
            "companies": None,
            "use_session": False,
        }

    user = session.get("user", {}) or {}
    user_id = user.get("id")
    user_role = user.get("role")
    companies = session.get("user_companies") or []

    return {
        "user_id": user_id,
        "user_role": user_role,
        "companies": companies if isinstance(companies, list) else [],
        "use_session": True,
    }


@dashboard_interno_mapa_bp.route("/api/processos", methods=["GET"])
@_apply_auth_decorators
def api_processos():
    """Retorna processos e metas para o dashboard."""
    context = _build_user_context()
    hoje = datetime.now()
    processos = _load_processes(
        user_id=context.get("user_id"),
        user_role=context.get("user_role"),
        user_companies=context.get("companies"),
        use_session=context.get("use_session", False),
    )
    meta = _load_meta(hoje.year, hoje.month)
    exchange_rates = _get_exchange_rates_safe()

    return jsonify(
        {
            "success": True,
            "data": {
                "processos": processos,
                "meta": meta,
                "exchange_rates": exchange_rates,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            },
        }
    )


@dashboard_interno_mapa_bp.route("/api/cache/clear", methods=["POST"])
@_apply_auth_decorators
def api_clear_cache():
    """Permite limpar o cache do dashboard para o usuário atual."""
    context = _build_user_context()

    if context.get("use_session"):
        session.pop(SESSION_CACHE_KEY, None)

    user_id = context.get("user_id")
    if user_id:
        data_cache.clear_user_cache(user_id)

    return jsonify({"success": True, "message": "Cache limpo com sucesso"})
