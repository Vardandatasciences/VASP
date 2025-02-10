from flask import Blueprint, request, jsonify,session,redirect,render_template,url_for

import os,shutil
from app.document_processing.utils import *
from app.document_processing.llm_processor import *
from app.document_processing.image_download import *
from app.document_processing.cloud import *
from app.auth.utils import *
from datetime import timedelta

from config.config import Config

UPLOAD_FOLDER = Config.UPLOAD_FOLDER
EXTRACTED_FOLDER = Config.EXTRACTED_FOLDER
EXCEL_FILE = Config.EXCEL_FILE
EXCEL_TEMPLATE=Config.EXCEL_TEMPLATE
REFERENCE_FOLDER=Config.REFERENCE_FOLDER
Excel_file_path=f"{REFERENCE_FOLDER}/{EXCEL_FILE}"


doc_bp = Blueprint('doc_processing', __name__,template_folder='templates')


@doc_bp.route('/upload', methods=['POST'])
def upload_file():
    # Ensure necessary folders exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(EXTRACTED_FOLDER, exist_ok=True)
    if 'doc-upload' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['doc-upload']
    category = request.form.get('category')
    print(category,' category is category----------------------------------------------------------------')
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        extracted_text = ""
        if file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            extracted_text = extract_text_from_image(file_path)
        elif file.filename.lower().endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_path, UPLOAD_FOLDER)
        else:
            return jsonify({"error": "Unsupported file type"}), 400

        output_txt_path = os.path.join(EXTRACTED_FOLDER, f"{os.path.splitext(file.filename)[0]}.txt")
        with open(output_txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(extracted_text)

        print(output_txt_path,'-----------------------------------------------------------------')
        print(f"{REFERENCE_FOLDER}/{EXCEL_TEMPLATE}/{EXCEL_FILE}",'----------------------------------------')

        # file_path = "extracted_text/tumbler_invoice.txt"  # Path to your text file
        # excel_path = "queries.xlsx"  # Path to the Excel file containing queries

        shutil.copy(f"{REFERENCE_FOLDER}/{EXCEL_TEMPLATE}/{EXCEL_FILE}", Excel_file_path)

        

        answer_queries_from_file_with_prompt(output_txt_path,Excel_file_path)


        

        data = read_excel_and_display()

        data_dict = {item['Name']: item['Answer'] for item in data}

        print(data_dict,'data_dict is data_dict----------------------------------------------------------------')

        
        # data_dict['category']=category
        
    
    # Get the order date string
        order_date_str = data_dict['Order Date']
        
        # Convert string to datetime object
        order_date_dt = standardize_date(order_date_str)
        if order_date_dt is None:
            raise ValueError(f"Unable to parse order date: {order_date_str}")
        
        # Calculate expiry date (order date + 1 year)
        # print('the order date is =================================',order_date_dt)
        expiry_date_dt = order_date_dt + timedelta(days=365)
        
        # Update the dictionary with standardized dates
        data_dict['Order Date'] = order_date_dt.strftime('%Y-%m-%d')
        data_dict['Expiry Date'] = expiry_date_dt.strftime('%Y-%m-%d')

        file_url=file_path.split('/')[-1].replace('\\', '/')
        # file_url_2=file_url.split('/')[-1]

        # input(file_url)

        session['file_path']=file_url[8:]

        if verify_aws_cli():
        # Example file upload
            # file_path = "static/uploads/tide_invoice.pdf"
            upload_to_s3_cli(file_url,session['username'])# Upload file to S3 using AWS CLI
        # print(data_dict)
        # print(file_url,'---------------------------------------------------------------------------')

        return render_template('results.html', data=data_dict , pdf_url=file_url)

@doc_bp.route('/save-edits', methods=['POST'])
def save_edits():
    """
    Save the edited fields back to the Excel file and handle 'Others' category.
    """
    try:
        # Debug: Print the incoming form data
        print("Incoming Form Data:", request.form)

        # Load the existing Excel file
        df = pd.read_excel(Excel_file_path)

        # Ensure 'Name' and 'Answer' columns exist
        if 'Name' not in df.columns or 'Answer' not in df.columns:
            df['Name'] = pd.Series(dtype='str')
            df['Answer'] = pd.Series(dtype='str')

        # Update the data in the DataFrame
        for name, value in request.form.items():
            if name.startswith("fields["):  # Look for keys starting with "fields["
                field_name = name[7:-1]  # Extract the field name (e.g., "Invoice Number")
                if field_name in df['Name'].values:
                    # Update the corresponding answer if the field exists
                    df.loc[df['Name'] == field_name, 'Answer'] = value
                else:
                    # Add a new row if the field_name does not exist
                    new_row = pd.DataFrame({'Name': [field_name], 'Answer': [value]})
                    df = pd.concat([df, new_row], ignore_index=True)

        # Save the updated DataFrame back to the Excel file
        df.to_excel(Excel_file_path, index=False)
        print("Excel file updated successfully!")

        data = read_excel_and_display()

        df = {item['Name']: item['Answer'] for item in data}

        print(df)
        product_brand=df['product brand']
        category_name=df['category']

        download_image_path=download_image_with_category_brand(category_name,product_brand)

        try:
            connection = connection_pool.get_connection()
            cursor = connection.cursor()

            cursor.execute("""   
                INSERT INTO product_images(product_name,product_image,category) 
                          VALUES (%s,%s,%s)""",
                          (product_brand,download_image_path,category_name))
            

            # Fixed INSERT statement - added %s for file_path
            cursor.execute(
                """
                INSERT INTO product_details (
                    user_name, platform_name, category, provider, product_brand, product_description, order_date, invoice_date,
                    gst_number, invoice_number, quantity, total_amount, discount_percentage, tax_amount,
                    igst_percentage, seller_address, billing_address, shipping_address, customer_name, pan_number, payement_mode, expiry_date, file_path
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    session['username'],
                    df['Platform Name'],
                    df['category'],
                    df['provider'],
                    df['product brand'],
                    df['product description'],
                    df['Order Date'],
                    df['Invoice date'],
                    df['GST number'],
                    df['Invoice Number'],
                    df['Quantity'],
                    df['Total Amount'],
                    df['Discount percentage'],
                    df['Tax amount'],
                    df['IGST percentage'],
                    df['Seller address'],
                    df['Billing Address'],
                    df['Shipping address'],
                    df['Customer Name'],
                    df['Pan No'],
                    df['Mode of Payement'],
                    df['Expiry Date'],
                    session['file_path']
                )
            )

            connection.commit()

        except Exception as e:
            print(f"Error inserting data: {e}")
            connection.rollback()
            # Add more detailed error logging
            import traceback
            print(traceback.format_exc())
        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('core.home'))
    except Exception as e:
        print(f"Error saving edits: {e}")
        return jsonify({"error": str(e)}), 500