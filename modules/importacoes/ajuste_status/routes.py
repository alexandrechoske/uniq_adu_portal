from flask import Blueprint, render_template, session
from routes.auth import login_required, role_required

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
    """Renderiza a página de ajuste de status com layout base."""
    return render_template("ajuste_status.html", user=session.get("user", {}))
