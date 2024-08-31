from flask import Blueprint, request, jsonify
from utils.db import get_db
from models.order import Order

order_bp = Blueprint('order_bp', __name__)
db = get_db()
order_model = Order(db)

@order_bp.route('/order', methods=['POST'])
def create_order():
    order_data = request.json
    order_model.create_order(order_data)
    return jsonify({"msg": "Order created successfully"}), 201

@order_bp.route('/order/<order_id>', methods=['GET'])
def get_order(order_id):
    order = order_model.get_order(order_id)
    return jsonify(order)
