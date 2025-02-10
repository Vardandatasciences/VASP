# app/auth/routes.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask import Flask, logging, render_template, request, send_file,redirect, url_for, session, jsonify, flash, make_response
from flask import current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
import os
from werkzeug.security import generate_password_hash, check_password_hash

from app.auth.utils import *
from config.config import Config

UPLOAD_FOLDER = Config.UPLOAD_FOLDER
EXTRACTED_FOLDER = Config.EXTRACTED_FOLDER
EXCEL_FILE = Config.EXCEL_FILE


from app.auth.utils import connection_pool

auth_bp = Blueprint('auth', __name__)


from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print("Session data:", session)  # Debugging session contents
        if 'username' not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function



def clear_session():
    session.clear()  # Clear all session data
    response = make_response(redirect(url_for('auth.login')))  # Redirect to login page
    response.set_cookie('session', '', expires=0)  # Clear the session cookie
    return response


# Logout route
@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    flash("You have been logged out successfully.", "success")
    return clear_session()

# Force session expiration when tab is closed
@auth_bp.before_request
def enforce_session_timeout():
    session.modified = True
    if 'username' in session:
        session.permanent = True  # Enforce timeout on every request

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    try:
        print("Entered login function")
        print(f"Current template folder: {current_app.template_folder}")  # Add this debug line
        session.clear()  # Clear session to ensure a fresh login
        
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            result = execute_query(
                "SELECT password, email, mode FROM users WHERE username = %s", 
                (username,)
            )
            if result:
                stored_password, email, mode = result[0]
                if check_password_hash(stored_password, password):
                    session['username'] = username
                    session['email'] = email
                    session.permanent = True
                    if mode == 'activate':
                        return redirect(url_for('core.home'))
                    else:
                        return redirect(url_for('auth.waiting'))
                else:
                    flash("Invalid credentials. Please try again.", "error")
            else:
                flash("Invalid credentials. Please try again.", "error")
        
        return render_template('login.html')
    except Exception as e:
        print(f"Error in login route: {str(e)}")  # Add error logging
        flash("An error occurred. Please try again.", "error")
        return render_template('login.html')


# Default index route
@auth_bp.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('core.home'))
    return redirect(url_for('auth.login'))


 
@auth_bp.route('/confirm_logout')
def confirm_logout():
    # Clear all data in the session to log out the user
    session.clear()
    # Redirect to the login screen
    return redirect(url_for('auth.login'))
 
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    countries = execute_query("SELECT name, country_code FROM countries")
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        country_code = request.form.get('country_code')
        mobile_number = request.form.get('mobile_number')
        location = request.form.get('location')
        pincode = request.form.get('pincode')

        if password and username and email and country_code and mobile_number and location and pincode:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            connection = connection_pool.get_connection()
            cursor = connection.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO users (username, password, email, country_code, mobile_number, location, pincode)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (username, hashed_password, email, country_code, mobile_number, location, pincode)
                )
                connection.commit()

                # Store username and email in session
                session['username'] = username
                session['email'] = email
            except Exception as e:
                print(f"Error inserting user: {e}")
                connection.rollback()
            finally:
                cursor.close()
                connection.close()
            
            # Redirect to payment page after successful signup
            return redirect(url_for('auth.payment_page'))

    return render_template('signup.html', countries=countries)



@auth_bp.route('/payment_page', methods=['GET'])
def payment_page():
    if 'email' not in session:  # Check if session exists
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for('auth.login'))
    
    # Pass session data to the payment page
    user_details = {
        'username': session.get('username'),
        'email': session.get('email'),
        'mobile_number': session.get('mobile_number')
    }
    return render_template('payment_page.html', user_details=user_details)

@auth_bp.route('/payment_upload', methods=['POST'])
def payment_upload():
    if 'email' not in session:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for('auth.login'))

    user_email = session['email']
    file = request.files.get('payment_screenshot')

    if not file or file.filename == '':
        flash("No file uploaded or selected.", "error")
        return redirect(url_for('auth.payment_page'))

    # Save the file
    upload_folder = os.path.join(os.getcwd(), 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    # Read the file in binary mode
    with open(filepath, 'rb') as f:
        binary_data = f.read()

    # Update the database
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE users
            SET payment_img = %s
            WHERE email = %s
        """, (binary_data, user_email))
        connection.commit()

        if cursor.rowcount > 0:
            flash("Payment screenshot uploaded successfully!", "success")

            # Check the user's mode
            cursor.execute("SELECT mode FROM users WHERE email = %s", (user_email,))
            mode_result = cursor.fetchone()
            if mode_result:
                user_mode = mode_result[0]
                if user_mode == 'activate':
                    return redirect(url_for('core.home'))
                else:
                    return redirect(url_for('auth.waiting'))
        else:
            flash("Failed to update payment screenshot. User not found.", "error")
    except Exception as e:
       
        flash("Error uploading payment screenshot. Please try again.", "error")
    finally:
        cursor.close()
        connection.close()

    # Default fallback
    return redirect(url_for('auth.login'))


@auth_bp.route('/waiting', methods=['GET'])
def waiting():
    if 'username' not in session:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for('auth.login'))
    
    username = session['username']
    return render_template('waiting.html', username=username)
