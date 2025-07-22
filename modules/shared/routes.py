"""
Shared Blueprint - Serves shared static files
"""
from flask import Blueprint

# Create shared blueprint for static files
shared_bp = Blueprint(
    'shared', 
    __name__,
    static_folder='static',
    static_url_path='/shared/static'
)

# Simple route for health check
@shared_bp.route('/shared/health')
def health():
    return {'status': 'ok', 'message': 'Shared blueprint is working'}
