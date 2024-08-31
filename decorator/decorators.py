from functools import wraps
from flask import session, redirect, url_for, flash
from utils.redis_client import get_redis_client
from datetime import datetime, timedelta

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'token' not in session:
            return redirect(url_for('auth.login'))

        redis_client = get_redis_client()
        user_id = redis_client.get(f"session:{session['token']}").decode('utf-8')
        user_role = redis_client.hget(f"user:{user_id}", "role").decode('utf-8')

        if user_role != 'admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('index'))

        return f(*args, **kwargs)
    return decorated_function



