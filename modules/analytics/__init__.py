"""
Analytics module for access logs dashboard
"""

from flask import Blueprint

# Import routes to ensure registration
from .routes import analytics_bp
