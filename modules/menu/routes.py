from flask import Blueprint, render_template

bp = Blueprint('menu', __name__,
    url_prefix='/menu',
    template_folder='templates',
    static_folder='static',
    static_url_path='/menu/static')

@bp.route('/')
def menu_home():
    return render_template('menu.html')

@bp.route('/dashboards')
def dashboards():
    return render_template('dashboards.html')

@bp.route('/ferramentas')
def ferramentas():
    return render_template('ferramentas.html')

@bp.route('/configuracoes')
def configuracoes():
    return render_template('configuracoes.html')
