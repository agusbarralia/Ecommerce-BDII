from flask import Blueprint, request, jsonify
from utils.db import get_db
from models.user import User

user_bp = Blueprint('user_bp', __name__)
db = get_db()
user_model = User(db)

@user_bp.route('/user', methods=['POST'])
def create_user():
    user_data = request.json
    user_model.create_user(user_data)
    return jsonify({"msg": "User created successfully"}), 201

@user_bp.route('/user/<user_id>', methods=['GET'])
def get_user(user_id):
    user = user_model.get_user(user_id)
    return jsonify(user)
