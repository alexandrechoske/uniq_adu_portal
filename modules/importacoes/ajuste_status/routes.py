from flask import Blueprint, render_template, session, jsonify, request
from routes.auth import login_required, role_required
from extensions import supabase_admin
from datetime import datetime

# Blueprint dedicado à tela de ajuste de status
ajuste_status_bp = Blueprint(
    "ajuste_status",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/ajuste-status/static",
    url_prefix="/ajuste-status",
)


@ajuste_status_bp.route("/", methods=["GET"])
@login_required
@role_required(["admin", "interno_unique"])
def index():
    """Renderiza a página de gerenciamento de mapeamento de status."""
    return render_template("ajuste_status.html", user=session.get("user", {}))


# ==================== API ENDPOINTS ====================

@ajuste_status_bp.route("/api/mappings", methods=["GET"])
@login_required
@role_required(["admin", "interno_unique"])
def get_mappings():
    """Lista todos os mapeamentos de status existentes."""
    try:
        response = supabase_admin.table("importacoes_status_timeline_mapping")\
            .select("*")\
            .order("timeline_order", desc=False)\
            .execute()
        
        return jsonify({
            "success": True,
            "data": response.data or []
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@ajuste_status_bp.route("/api/mappings", methods=["POST"])
@login_required
@role_required(["admin", "interno_unique"])
def create_mapping():
    """Cria um novo mapeamento de status."""
    try:
        data = request.get_json()
        
        # Validação básica
        if not data.get("status_sistema") or not data.get("status_timeline") or data.get("timeline_order") is None:
            return jsonify({
                "success": False,
                "error": "Campos obrigatórios faltando"
            }), 400
        
        # Inserir novo mapeamento
        new_mapping = {
            "status_sistema": data["status_sistema"].strip().upper(),
            "status_timeline": data["status_timeline"],
            "timeline_order": int(data["timeline_order"]),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = supabase_admin.table("importacoes_status_timeline_mapping")\
            .insert(new_mapping)\
            .execute()
        
        return jsonify({
            "success": True,
            "data": response.data[0] if response.data else new_mapping
        })
    except Exception as e:
        error_msg = str(e)
        if "duplicate key" in error_msg.lower():
            return jsonify({
                "success": False,
                "error": "Este status do sistema já possui um mapeamento"
            }), 409
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500


@ajuste_status_bp.route("/api/mappings/<status_sistema>", methods=["PUT"])
@login_required
@role_required(["admin", "interno_unique"])
def update_mapping(status_sistema):
    """Atualiza um mapeamento existente."""
    try:
        data = request.get_json()
        
        # Validação básica
        if not data.get("status_timeline") or data.get("timeline_order") is None:
            return jsonify({
                "success": False,
                "error": "Campos obrigatórios faltando"
            }), 400
        
        # Atualizar mapeamento
        update_data = {
            "status_timeline": data["status_timeline"],
            "timeline_order": int(data["timeline_order"]),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        response = supabase_admin.table("importacoes_status_timeline_mapping")\
            .update(update_data)\
            .eq("status_sistema", status_sistema)\
            .execute()
        
        if not response.data:
            return jsonify({
                "success": False,
                "error": "Mapeamento não encontrado"
            }), 404
        
        return jsonify({
            "success": True,
            "data": response.data[0]
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@ajuste_status_bp.route("/api/mappings/<status_sistema>", methods=["DELETE"])
@login_required
@role_required(["admin", "interno_unique"])
def delete_mapping(status_sistema):
    """Deleta um mapeamento de status."""
    try:
        response = supabase_admin.table("importacoes_status_timeline_mapping")\
            .delete()\
            .eq("status_sistema", status_sistema)\
            .execute()
        
        if not response.data:
            return jsonify({
                "success": False,
                "error": "Mapeamento não encontrado"
            }), 404
        
        return jsonify({
            "success": True,
            "message": "Mapeamento excluído com sucesso"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@ajuste_status_bp.route("/api/unmapped-statuses", methods=["GET"])
@login_required
@role_required(["admin", "interno_unique"])
def get_unmapped_statuses():
    """Retorna lista vazia - usuário deve digitar manualmente novos status."""
    try:
        print("� [AJUSTE STATUS] Endpoint de status não mapeados chamado")
        print("ℹ️  [AJUSTE STATUS] Retornando lista vazia - novos status devem ser digitados manualmente")
        
        # Retornar lista vazia - usuário digitará manualmente
        return jsonify({
            "success": True,
            "data": []
        })
    except Exception as e:
        print(f"❌ [AJUSTE STATUS] Erro: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "data": []
        }), 200
