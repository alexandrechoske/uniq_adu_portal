from flask import Blueprint, request, jsonify, session
from extensions import supabase
from routes.auth import login_required

bp = Blueprint('api', __name__)

# Any other API endpoints can go here
