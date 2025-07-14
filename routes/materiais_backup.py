from flask import Blueprint, render_template, session, request, jsonify
from routes.auth import login_required, role_required
from permissions import check_permission

bp = Blueprint('materiais', __name__)

@bp.route('/')
@login_required
@role_required(['admin', 'interno_unique', 'cliente_unique'])
def index():
    """Página principal de materiais - nova versão"""
    return render_template('materiais/index.html')
