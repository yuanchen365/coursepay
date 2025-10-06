from flask import Blueprint
bp = Blueprint("speech", __name__)
from . import routes  # noqa
