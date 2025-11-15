from flask import Blueprint

bp = Blueprint('responses', __name__)

from app.responses import routes