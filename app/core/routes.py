from flask import Blueprint, request, session, render_template,send_file
import os

from app.auth.utils import *

from config.config import Config
from app.document_processing.cloud import download_from_s3_cli

UPLOAD_FOLDER = Config.UPLOAD_FOLDER
EXTRACTED_FOLDER = Config.EXTRACTED_FOLDER
EXCEL_FILE = Config.EXCEL_FILE


core_bp = Blueprint('core', __name__,template_folder='templates')



@core_bp.route('/upload', methods=['GET'])
def upload():
    return render_template('upload.html')


@core_bp.route('/home', methods=['GET'])
def home():
    if 'username' not in session:
        flash("Session expired. Please log in again.", "error")
        return redirect(url_for('auth.login'))
    
    username = session['username']
    result = execute_query("SELECT mode FROM users WHERE username = %s", (username,))
    connection = connection_pool.get_connection()
    
    try:
        cursor = connection.cursor()
        
        # Fetch categories for dropdown
        cursor.execute("SELECT category FROM product_images")
        categories = [row[0] for row in cursor.fetchall()]

        # Fetch product details with images
        cursor.execute("SELECT * FROM product_details where user_name = %s",(session['username'],))
        product_details = cursor.fetchall()

        # Append product images
        products_with_images = []
        for product in product_details:
            cursor.execute(
                "SELECT product_image FROM product_images WHERE category = %s LIMIT 1",
                (product[3],)
            )
            image = cursor.fetchone()

            # Check if image exists before trying to decode
            if image and image[0]:
                image_link = image[0].decode('utf-8')

                
            else:
                image_link = 'static/images/products/unknown.png'

            print(image_link)
            
            # Add both image_link and expiry_date to the product tuple
            products_with_images.append(product + (image_link,))

        print(products_with_images,'--------------------------------')
    finally:
        cursor.close()
        connection.close()

    if result:
        # print(products_with_images)
        mode = result[0][0]  # Extract mode from the query result
        if mode == 'activate':
            return render_template(
                'home.html',
                username=username,
                categories=categories,
                products=products_with_images
            )
        else:
            return redirect(url_for('waiting'))
    else:
        flash("User mode not found. Please contact support.", "error")
        return redirect(url_for('auth.login'))

@core_bp.route('/products')
def display_products():
    print('-------------------------------- producst page called --------------------------------')
    connection = connection_pool.get_connection()
    with connection:
        with connection.cursor() as cursor:
            # Fetch product details
            cursor.execute("SELECT * FROM product_details where user_name = %s",(session['username'],))
            product_details = cursor.fetchall()
            
            # Fetch product images based on category
            products_with_images=[]
            for product in product_details:
                cursor.execute(
                    "SELECT product_image FROM product_images WHERE category = %s LIMIT 1",
                    (product[3],)
                )
                image = cursor.fetchone()
                image_link = image[0].decode('utf-8') if image else 'static/images/products/default_image.jpg'
                
                # Debugging: Print the image link
                print(f"Image link for product {product[5]}: {image_link}")

                # Append a new tuple combining product details and image
                products_with_images.append(product + (image_link,))

    print(products_with_images,'--------------------------------')
                
    return render_template('products.html', products=products_with_images)


@core_bp.route('/services', methods=['GET', 'POST'])
def services():
    username = session.get('username')  # Remove trailing comma
    
    connection = connection_pool.get_connection()
    cursor = connection.cursor()

    # Fetch categories for the user
    cursor.execute("SELECT DISTINCT category FROM product_details WHERE user_name = %s", (username,))
    categories = [row[0] for row in cursor.fetchall()]

    # Fetch products for the first category (optional default behavior)
    products = []
    if categories:
        cursor.execute("SELECT product_brand FROM product_details WHERE user_name = %s AND category = %s", (username, categories[0]))
        products = [row[0] for row in cursor.fetchall()]
    
    connection.close()

    return render_template('services.html', categories=categories, products=products)



@core_bp.route('/get-products', methods=['POST'])
def get_products():
    username = session.get('username')
    selected_category = request.json.get('category')  # Expecting JSON input
    
    connection = connection_pool.get_connection()
    cursor = connection.cursor()

    # Fetch products for the selected category
    cursor.execute("SELECT product_brand FROM product_details WHERE user_name = %s AND category = %s", (username, selected_category))
    products = [row[0] for row in cursor.fetchall()]
    
    connection.close()

    return jsonify(products)
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime

@core_bp.route('/submit-complaint', methods=['POST'])
def submit_complaint():
    category = request.form['category']
    product = request.form['product']
    issue = request.form['issue']
    username = session.get('username')

    connection = connection_pool.get_connection()
    cursor = connection.cursor()

    # Insert the complaint into the database
    cursor.execute(
        "INSERT INTO complaint_details (user_name, category, product, complaint, complaint_date) VALUES (%s, %s, %s, %s, %s)",
        ( username,category, product, issue, datetime.now())
    )
    connection.commit()

    # Get the current date
    current_date = datetime.now().date()

    # Fetch the expiry date for the selected product
    cursor.execute(
        "SELECT expiry_date FROM product_details WHERE user_name = %s AND category = %s AND product_brand = %s",
        (username, category, product)
    )
    result = cursor.fetchone()
    connection.close()

    if result:
        expiry_date = datetime.strptime(result[0], '%Y-%m-%d').date()

        # Check if the product is within the warranty period
        if current_date <= expiry_date:
            flash("Your product is within warranty. We will raise your complaint.", "success")
        else:
            flash("Your product is out of warranty. Additional charges may apply.", "warning")
    else:
        flash("Error: Could not retrieve product details.", "error")

    return redirect(url_for('core.services'))



@core_bp.route('/download-pdf', methods=['POST'])
def download_pdf():
    try:
        # Get the PDF path from the request
        data = request.json
        pdf_path = data.get('path')
        # input(pdf_path)
        
        if not pdf_path:
            return jsonify({'error': 'No file path provided'}), 400
            
        # Get the filename from the path
        file_name = os.path.basename(pdf_path)
        
        # Download the file from S3
        local_file_path = download_from_s3_cli(
            user_name=session.get('username'),
            file_name=file_name
        )
        
        if not local_file_path or not os.path.exists(local_file_path):
            return jsonify({'error': 'File not found in S3'}), 404
            
        # Send the file to the user
        try:
            return send_file(
                local_file_path,
                as_attachment=True,
                download_name=file_name
            )
        finally:
            # Clean up the temporary file after sending
            try:
                os.remove(local_file_path)
            except Exception as e:
                print(f"Error removing temporary file: {e}")
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

