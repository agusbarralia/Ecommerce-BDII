from flask import Blueprint, request, jsonify
from utils.db import get_db
from models.product import Product

product_bp = Blueprint('product_bp', __name__)
db = get_db()
product_model = Product(db)

@product_bp.route('/product', methods=['POST'])
def create_product():
    product_data = request.json
    product_model.create_product(product_data)
    return jsonify({"msg": "Product created successfully"}), 201

@product_bp.route('/product/<product_id>', methods=['GET'])
def get_product(product_id):
    product = product_model.get_product(product_id)
    return jsonify(product)

@product_bp.route('/product/<product_id>', methods=['PUT'])
def update_product(product_id):
    update_data = request.json
    product_model.update_product(product_id, update_data)
    return jsonify({"msg": "Product updated successfully"})

@product_bp.route('/product/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    product_model.delete_product(product_id)
    return jsonify({"msg": "Product deleted successfully"})

@product_bp.route('/products', methods=['GET'])
def get_all_products():
    products = product_model.get_all_products()
    return jsonify(products)
