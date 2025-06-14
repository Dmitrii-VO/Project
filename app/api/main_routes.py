from flask import Blueprint, render_template, jsonify, request
from app.services.auth_service import auth_service
from app.models.database import db_manager
from app.config.settings import Config
import os
import logging

logger = logging.getLogger(__name__)
main_bp = Blueprint('main_routes', __name__)

