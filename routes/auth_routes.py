from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from utils.redis_client import get_redis_client
import uuid
import hashlib
import time
from utils.classify_users import classify_user  

auth_bp = Blueprint('auth', __name__)
redis_client = get_redis_client()

auth_bp = Blueprint('auth', __name__)
redis_client = get_redis_client()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        username = data.get('username')
        password = data.get('password')
        name = data.get('name')
        address = data.get('address')
        id_number = data.get('id_number')
        
        if not username or not password or not name or not address or not id_number:
            return render_template('register.html', error="All fields are required")

        if redis_client.exists(f"user:{username}"):
            return render_template('register.html', error="Username already exists")

        hashed_password = hash_password(password)
        user_data = {
            "username": username,
            "password": hashed_password,
            "name": name,
            "address": address,
            "id_number": id_number,
            "role": "client"
        }
        redis_client.hset(f"user:{username}", mapping=user_data)
        
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return render_template('login.html', error="Username and password are required")

        hashed_password = hash_password(password)
        stored_password = redis_client.hget(f"user:{username}", "password")
        stored_password = stored_password.decode('utf-8') if stored_password else None

        print(f"Login - Username: {username}, Hashed Password: {hashed_password}, Stored Password: {stored_password}") 
        
        if not stored_password or stored_password != hashed_password:
            return render_template('login.html', error="Invalid username or password")

        session_token = str(uuid.uuid4())
        redis_client.set(f"session:{session_token}", username)
        redis_client.expire(f"session:{session_token}", 3600)  # La sesion expira en una hora
        session['token'] = session_token

        login_time = time.time()
        redis_client.hset(f"user:{username}", "login_time", login_time)

        return redirect(url_for('index'))

    return render_template('login.html')

@auth_bp.route('/logout', methods=['POST'])
def logout():
    token = session.get('token')
    
    if not token:
        return redirect(url_for('auth.login'))

    username = redis_client.get(f"session:{token}").decode('utf-8')
    login_time = float(redis_client.hget(f"user:{username}", "login_time"))
    logout_time = time.time()
    
    session_duration = logout_time - login_time
    
    # Actualizar el tiempo total de conexión diario
    current_date = time.strftime("%Y-%m-%d")
    key = f"user:{username}:connection_time:{current_date}"
    total_time = redis_client.get(key)

    if total_time:
        total_time = float(total_time)
    else:
        total_time = 0.0
    
    total_time += session_duration
    redis_client.set(key, total_time)

    classify_user(username)

    redis_client.delete(f"session:{token}")
    session.pop('token', None)

    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
def profile():
    token = session.get('token')
    if not token or not redis_client.exists(f"session:{token}"):
        return redirect(url_for('auth.login'))
    
    username = redis_client.get(f"session:{token}").decode('utf-8')
    user_data = redis_client.hgetall(f"user:{username}")
    user = {k.decode('utf-8'): v.decode('utf-8') for k, v in user_data.items()}
    return render_template('profile.html', user=user)

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        id_number = request.form['dni']
        new_password = request.form['password']
        # Verificar que el nombre y el DNI coinciden
        stored_dni = redis_client.hget(f"user:{email}", "id_number").decode('utf-8')
        if stored_dni == id_number:
            hashed_password = hash_password(new_password)
            redis_client.hset(f"user:{email}", "password", hashed_password)
            return render_template('login.html')
        else:
            return "Invalid email or DNI"
            
        
    return render_template('reset_password.html')