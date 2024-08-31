from flask import Flask, render_template, request, redirect, url_for, session
from routes.user_routes import user_bp
from routes.cart_routes import cart_bp
from routes.order_routes import order_bp
from routes.product_routes import product_bp
from routes.auth_routes import auth_bp
from utils.db import get_db
from utils.redis_client import get_redis_client
from models.product import Product
from models.cart import Cart
from models.payment import Payment
from models.order import Order
from models.invoice import Invoice
from decorator.decorators import admin_required
from werkzeug.utils import secure_filename
import os
from bson import json_util, ObjectId
from datetime import datetime, timedelta

secret_key = os.urandom(24)

app = Flask(__name__)
app.secret_key = secret_key  #Para usar sesiones en Flask

#Registramos blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(cart_bp, url_prefix='/api')
app.register_blueprint(order_bp, url_prefix='/api')
app.register_blueprint(product_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/auth')

#Configuramos la carpeta de subida
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_cart_count():
    if 'token' not in session:
        return 0
    redis_client = get_redis_client()
    user_id = redis_client.get(f"session:{session['token']}").decode('utf-8')
    db = get_db()
    cart_model = Cart(db)
    cart_id = f"{user_id}"
    items = cart_model.get_cart(cart_id)
    if items:
        return sum(item["quantity"] for item in items)
    return 0

@app.context_processor
def inject_user_role():
    if 'token' not in session:
        return dict(user_role=None)
    
    redis_client = get_redis_client()
    user_id = redis_client.get(f"session:{session['token']}").decode('utf-8')
    user_role = redis_client.hget(f"user:{user_id}", "role").decode('utf-8')
    
    return dict(user_role=user_role)

@app.context_processor
def inject_cart_count():
    return dict(cart_count=get_cart_count())

@app.route('/')
def index():
    db = get_db()
    product_model = Product(db)
    products = product_model.get_active_products()  
    return render_template('home.html', products=products)

#Pantalla donde se muestran todos los articulos subidos
@app.route('/products')
def products_page():
    db = get_db()
    product_model = Product(db)
    products = product_model.get_active_products()
    return render_template('products.html', products=products)

#Detalle del producto 
@app.route('/product/<product_id>')
def product_detail(product_id):
    db = get_db()
    product_model = Product(db)
    product = product_model.get_product(product_id)
    if not product:
        return "Product not found", 404
    return render_template('product_detail.html', product=product)

#Busca el producto desde la pantalla home
@app.route('/search')
def search():
    query = request.args.get('q')
    db = get_db()
    product_model = Product(db)
    products = list(product_model.collection.find({"name": {"$regex": query, "$options": "i"}}))
    return render_template('products.html', products=products)

#Panel de control para el ADMIN
@app.route('/admin/products')
@admin_required
def admin_products_page():
    db = get_db()
    product_model = Product(db)
    products = product_model.get_active_products_admin()
    return render_template('admin_products.html', products=products)

@app.route('/admin/add_product', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        images = []

        if 'image_files' in request.files:
            for file in request.files.getlist('image_files'):
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    images.append(f'/uploads/{filename}')

        #Creo un nuevo producto
        db = get_db()
        product_model = Product(db)
        product_data = {
            "productId": str(ObjectId()),
            "name": name,
            "price": price,
            "description": description,
            "stock": stock,
            "images": images,
            "isDeleted": False
        }
        product_model.add_product(product_data)

        #Registramos las acciones en auditoría
        user_id = get_redis_client().get(f"session:{session['token']}").decode('utf-8')
        log_audit("create", product_data["productId"], user_id, f"Product '{name}' created")

        return redirect(url_for('admin_products_page'))

    return render_template('add_product.html')

@app.route('/admin/edit_product/<product_id>', methods=['GET', 'POST'])
@admin_required

#El usuario con rol ADMIN puede editar los productos
def edit_product(product_id):
    db = get_db()
    product_model = Product(db)
    
    if request.method == 'POST':
        product = product_model.get_product(product_id)
        
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        images = product['images']

        changes = []
        if name != product["name"]:
            changes.append({"field": "name", "old": product["name"], "new": name})
        if price != product["price"]:
            changes.append({"field": "price", "old": product["price"], "new": price})
        if stock != product["stock"]:
            changes.append({"field": "stock", "old": product["stock"], "new": stock})
        if description != product["description"]:
            changes.append({"field": "description", "old": product["description"], "new": description})
        
        if 'image_files' in request.files:
            for file in request.files.getlist('image_files'):
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    images.append(f'uploads/{filename}')  #Agregamos la nueva imagen a la lista

        product_data = {
            "name": name,
            "price": price,
            "description": description,
            "stock": stock,
            "images": images
        }
        product_model.update_product(product_id, product_data)

        #Aca se registra la acción en auditoría
        user_id = get_redis_client().get(f"session:{session['token']}").decode('utf-8')
        log_audit("edit", product_id, user_id, f"Product '{name}' updated", changes)

        return redirect(url_for('admin_products_page'))

    product = product_model.get_product(product_id)
    return render_template('edit_product.html', product= product)

@app.route('/admin/delete_product/<product_id>', methods=['POST'])
@admin_required

#El usuario con rol ADMIN puede borrar los productos
def delete_product(product_id):
    db = get_db()
    product_model = Product(db)
    product = product_model.get_product(product_id)

    if product:
        product_model.delete_product(product_id)

        #Se registra la acción en auditoría
        user_id = get_redis_client().get(f"session:{session['token']}").decode('utf-8')
        log_audit("delete", product_id, user_id, f"Product '{product['name']}' deleted")

    return redirect(url_for('admin_products_page'))

#Función para registrarlo en auditoría
def log_audit(action, product_id, user_id, details, changes=None):
    db = get_db()
    audit_log = {
        "action": action,
        "product_id": product_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow(),
        "details": details,
        "changes": changes  #Aca mostramos los cambios
    }
    db.audit_logs.insert_one(audit_log)

@app.route('/admin/audit_logs')
@admin_required

#El usuario con rol ADMIN puede ver lo que ocurre en la Auditoria
def view_audit_logs():
    db = get_db()
    audit_logs = list(db.audit_logs.find().sort("timestamp", -1))
    return render_template('admin_audit_logs.html', audit_logs=audit_logs)

@app.route('/admin/audit_logs/<product_id>')
@admin_required
def view_product_audit_logs(product_id):
    db = get_db()
    audit_logs = list(db.audit_logs.find({"product_id": product_id}).sort("timestamp", -1))
    product = db.products.find_one({"productId": product_id})
    return render_template('product_audit_logs.html', audit_logs=audit_logs, product=product)

#El usuario puede agregar cosa a su carrito
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'token' not in session:
        return redirect(url_for('auth.login'))
    
    redis_client = get_redis_client()
    user_id = redis_client.get(f"session:{session['token']}").decode('utf-8')
    product_id = request.form['product_id']
    product_name = request.form['name']
    quantity = int(request.form['quantity'])

    db = get_db()
    cart_model = Cart(db)
    cart_id = f"{user_id}"
    cart_model.add_to_cart(cart_id, product_id, quantity, product_name)
    
    return redirect(url_for('products_page'))

#El usuario puede ver su carrito
@app.route('/cart')
def view_cart():
    if 'token' not in session:
        return redirect(url_for('auth.login'))
    
    redis_client = get_redis_client()
    user_id = redis_client.get(f"session:{session['token']}").decode('utf-8')
    db = get_db()
    cart_model = Cart(db)
    cart_id = f"{user_id}"
    items = cart_model.get_cart(cart_id)
    return render_template('cart.html', items=items)


#El usuario puede actualizar su carrito
@app.route('/update_cart', methods=['POST'])
def update_cart():
    if 'token' not in session:
        return redirect(url_for('auth.login'))
    redis_client = get_redis_client()
    user_id = redis_client.get(f"session:{session['token']}").decode('utf-8')
    product_id = request.form['product_id']
    quantity = int(request.form['quantity'])

    db = get_db()
    cart_model = Cart(db)
    cart_id = f"{user_id}"
    cart_model.update_cart_quantity(cart_id, product_id, quantity)
    
    return redirect(url_for('view_cart'))

#El usuario puede eliminar productos de su carrito
@app.route('/remove_from_cart/<product_id>', methods=['POST'])
def remove_from_cart(product_id):
    if 'token' not in session:
        return redirect(url_for('auth.login'))
    redis_client = get_redis_client()
    user_id = redis_client.get(f"session:{session['token']}").decode('utf-8')
    db = get_db()
    cart_model = Cart(db)
    cart_id = f"{user_id}"
    cart_model.remove_from_cart(cart_id, product_id)
    return redirect(url_for('view_cart'))

#El checkout me muestra todo lo que tiene el carrito con su precio y demas
@app.route('/checkout/<order_number>', methods=['GET'])
def checkout(order_number):
    if 'token' not in session:
        return redirect(url_for('auth.login'))
    
    redis_client = get_redis_client()
    user_id = redis_client.get(f"session:{session['token']}").decode('utf-8')
    db = get_db()
    
    order_model = Order(db)
    order = order_model.get_order(order_number)

    if not order:
        return "Order not found", 404

    #Se obtienen los detalles del producto
    product_model = Product(db)
    detailed_items = []
    for item in order['items']:
        product = product_model.get_product(item['productId'])
        item_details = {
            "name": product['name'],
            "price": product['price'],
            "quantity": item['quantity']
        }
        detailed_items.append(item_details)

    total = sum(item['quantity'] * get_product_price(item['productId'], db) for item in order['items'])
    return render_template('checkout.html', items=detailed_items, total=total, order_number=order_number)

#Trae el precio del producto
def get_product_price(product_id, db):
    product_model = Product(db)
    product = product_model.get_product(product_id)
    return product['price']

#Pantalla de error en caso de que estes en el carrito y un producto no tenga mas stock 
@app.route('/error')
def error():
    return render_template('error.html')

#Proceso de pago 
@app.route('/process_payment/<order_number>', methods=['POST'])
def process_payment(order_number):
    if 'token' not in session:
        return redirect(url_for('auth.login'))
    
    redis_client = get_redis_client()
    user_id = redis_client.get(f"session:{session['token']}").decode('utf-8')

    user_name = redis_client.hget(f"user:{user_id}", "name").decode('utf-8')
    user_address = redis_client.hget(f"user:{user_id}", "address").decode('utf-8')

    payment_method = request.form['payment_method']
    installments = request.form.get('installments', '1')
    iva_value = float(request.form.get('iva_value', 0))
    final_total = float(request.form.get('final_total', 0))
    total_fee = float(request.form.get('credit_fee_amount', 0))

    db = get_db()
    payment_model = Payment(db)
    order_model = Order(db)
    product_model = Product(db)
    invoice_model = Invoice(db) 
    iva_condition = request.form.get('iva_condition')  

    order = order_model.get_order(order_number)
    if not order:
        return "Order not found", 404

    total = order['total']

    payment_info = {
        "user_id": user_id,
        "payment_method": payment_method,
        "installments": int(installments),
        "total": total,
        "final_total": final_total,
        "total_fee": total_fee,
        "items": order['items'],
        "order_number": int(order_number),
        "iva": iva_value
    }

    invoice_number = invoice_model.get_next_invoice_number()

    invoice_info = {
        "invoice_number": invoice_number,
        "user_id": user_id,
        "name": user_name,
        "address": user_address,
        "payment_method": payment_method,
        "installments": int(installments),
        "total_fee": total_fee,
        "total": total,
        "final_total": final_total,
        "items": order['items'],
        "order_number": int(order_number),
        "iva": iva_value,
        "iva_condition": iva_condition,
        "date": datetime.utcnow()
    }

    #Utiliza el modelo Payment para guardar la información del pago
    payment_model.insert_payment(payment_info)

    #Actualiza el estado de la orden a "Pagado"
    order_model.update_order_status(int(order_number), "Pagado")

    invoice_id = invoice_model.create_invoice(invoice_info)

    #Establece un indicador de que el pago fue exitoso y guarda la info de pago en la sesión
    session['payment_completed'] = True
    session['payment_info'] = json_util.dumps(payment_info)  
    session['invoice_id'] = invoice_id

    return redirect(url_for('payment_success'))

#Funcion que te redirige hacia la pantalla 
@app.route('/view_invoice/<order_id>', methods=['GET'])
def view_invoice(order_id):
    db = get_db()
    invoice_model = Invoice(db)

    invoice_info = invoice_model.get_invoice_by_orderId(order_id)
    
    if not invoice_info:
        return "Invoice not found", 404

    return render_template('view_invoice.html', invoice_info=invoice_info)

#Pantalla con ya todo pago 
@app.route('/payment_success')
def payment_success():
    #Verifica si el pago fue completado
    if 'payment_completed' in session and session['payment_completed']:
        #Obtener informacion de la sesion y luego eliminar el indicador de la sesion
        payment_info = json_util.loads(session.get('payment_info'))
        session.pop('payment_completed', None)
        session.pop('payment_info', None)
       
        return render_template('payment_success.html', payment_info=payment_info)
    else:
        return redirect(url_for('index'))

#El usuario con rol ADMIN puede ver todas las ordenes
@app.route('/admin/orders')
@admin_required
def view_all_orders():
    db = get_db()
    order_model = Order(db)
    orders = order_model.get_all_orders()
    return render_template('admin_orders.html', orders=orders)

#Ordenes de los usuarios
@app.route('/user/orders')
def user_orders():
    if 'token' not in session:
        return redirect(url_for('auth.login'))
    
    redis_client = get_redis_client()
    user_id = redis_client.get(f"session:{session['token']}").decode('utf-8')
    
    db = get_db()
    order_model = Order(db)
    
    #Obtiene las ordenes del usuario
    orders = order_model.get_orders_by_user(user_id)
    
    return render_template('user_orders.html', orders=orders)

#Se crean las ordenes
@app.route('/create_order', methods=['POST'])
def create_order():
    if 'token' not in session:
        return redirect(url_for('auth.login'))
    
    redis_client = get_redis_client()
    db = get_db()

    user_id = redis_client.get(f"session:{session['token']}").decode('utf-8')
    user_name = redis_client.hget(f"user:{user_id}", "name").decode('utf-8')
    user_address = redis_client.hget(f"user:{user_id}", "address").decode('utf-8')

    order_number = redis_client.incr('order_number')
    print(order_number)

    cart_model = Cart(db)
    order_model = Order(db)
    product_model = Product(db)

    cart_model = Cart(db)
    cart_id = f"{user_id}"
    items = cart_model.get_cart(cart_id)
    total = sum(item['quantity'] * get_product_price(item['productId'], db) for item in items)

    #Maneja los casos donde no hay suficiente stock
    for item in items:
        item["productId"] = str(item["productId"])
        product = product_model.get_product(item["productId"])        
        if product["stock"] < item["quantity"]:
            return redirect(url_for('error'))

        item_price = get_product_price(item["productId"], db)
        item["price"] = item_price

    for item in items:
        product_model.decrement_stock(item["productId"], item["quantity"])

    order_info = {
        "order_number": order_number,
        "user_id": user_id,
        "name": user_name,
        "address": user_address,
        "items": items,
        "total": total,
        "status": "Pendiente de pago"
    }
        # Utilizar el modelo Order para guardar la información de la orden
    order_model.insert_order(order_info)
    cart_model.update_cart(cart_id, {"items": []})
    
    return redirect(url_for('view_order_details', order_id=order_number))

#Te lleva a ver todas las ordenes que tuvo el usuario en la pagina web solo si tenes ROL CLIENT
@app.route('/order/<order_id>') 
def view_order_details(order_id):
    if 'token' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    order_model = Order(db)
    order = order_model.get_order(order_id)
    if not order:
        return "Order not found", 404
    return render_template('user_order_details.html', order=order)

#Te lleva a ver todas las ordenes que tuvo la pagina web solo si tenes ROL ADMIN
@app.route('/admin/order/<order_id>') 
@admin_required
def view_admin_order_details(order_id):
    db = get_db()
    order_model = Order(db)
    order = order_model.get_order(order_id)
    if not order:
        return "Order not found", 404
    return render_template('admin_order_details.html', order=order)

#Testeamos que ande la base de datos MONGO
@app.route('/test_mongo')
def test_mongo():
    db = get_db()
    try:
        db.command("ping")
        return "MongoDB connection successful!"
    except Exception as e:
        return str(e)

#Testeamos que ande la base de datos REDIS   
@app.route('/test_redis')
def test_redis():
    redis = get_redis_client()
    try:
        redis.ping()
        return "Conexión a Redis exitosa."
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    app.run(debug=True)