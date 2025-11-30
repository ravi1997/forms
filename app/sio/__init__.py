from flask import Blueprint

bp = Blueprint('sio', __name__)

from app.sio import events
