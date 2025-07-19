from flask import Blueprint, render_template

bp = Blueprint('menu', __name__,
    url_prefix='/menu',
    template_folder='templates',
    static_folder='static',
    static_url_path='/menu/static')

@bp.route('/')
def menu_home():
    return render_template('menu.html')
