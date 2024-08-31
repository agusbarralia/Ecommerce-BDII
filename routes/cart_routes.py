from flask import Blueprint, request, jsonify
from utils.db import get_db
from models.cart import Cart

cart_bp = Blueprint('cart_bp', __name__)
db = get_db()
cart_model = Cart(db)

@cart_bp.route('/cart', methods=['POST'])
def create_cart():
    cart_data = request.json
    cart_model.create_cart(cart_data)
    return jsonify({"msg": "Cart created successfully"}), 201

@cart_bp.route('/cart/<cart_id>', methods=['GET'])
def get_cart(cart_id):
    cart = cart_model.get_cart(cart_id)
    return jsonify(cart)

@cart_bp.route('/cart/<cart_id>', methods=['PUT'])
def update_cart(cart_id):
    update_data = request.json
    cart_model.update_cart(cart_id, update_data)
    return jsonify({"msg": "Cart updated successfully"})

@cart_bp.route('/cart/<cart_id>', methods=['DELETE'])
def delete_cart(cart_id):
    cart_model.delete_cart(cart_id)
    return jsonify({"msg": "Cart deleted successfully"})
