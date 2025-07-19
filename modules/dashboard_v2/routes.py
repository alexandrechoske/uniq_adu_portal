from flask import Blueprint, render_template

bp = Blueprint('dashboard_v2', __name__, url_prefix='/dashboard-v2', template_folder='templates')

@bp.route('/')
def index():
    return render_template('index.html')
