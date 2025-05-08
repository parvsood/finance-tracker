from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
import datetime
from functools import wraps
import os
import sqlite3
import pytesseract
from PIL import Image
import cv2
import numpy as np
import tempfile
import re
import time

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = 'your_secret_key'
app.config['DATABASE'] = '../db.sqlite3'
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

def get_db_connection():
    conn = sqlite3.connect(
        app.config['DATABASE'],
        timeout=30.0,
        isolation_level=None
    )
    conn.row_factory = sqlite3.Row
    return conn

def execute_with_retry(query, params=(), fetchone=False, fetchall=False, commit=False, max_retries=5):
    retries = 0
    while retries < max_retries:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            result = None
            if fetchone:
                result = cursor.fetchone()
            elif fetchall:
                result = cursor.fetchall()
            
            if commit:
                conn.commit()
                
            conn.close()
            return result
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and retries < max_retries - 1:
                retries += 1
                time.sleep(0.5 * retries)
                continue
            raise
        finally:
            if 'conn' in locals() and conn:
                conn.close()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated
    
@app.route('/api/auth', methods=['POST'])
def authenticate():
    data = request.json
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing username or password!'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    user = execute_with_retry(
        'SELECT * FROM auth_user WHERE username = ?', 
        (username,), 
        fetchone=True
    )
    
    if not user:
        return jsonify({'message': 'User not found!'}), 401
    
    token = jwt.encode({
        'user_id': user['id'],
        'username': user['username'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    
    return jsonify({'token': token})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing required fields!'}), 400
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    phone = data.get('phone', '')

    existing_user = execute_with_retry(
        'SELECT * FROM auth_user WHERE username = ?', 
        (username,), 
        fetchone=True
    )
    
    if existing_user:
        return jsonify({'message': 'Username already exists!'}), 400

    execute_with_retry(
        '''
        INSERT INTO auth_user (username, email, password, first_name, last_name, is_superuser, is_staff, is_active, date_joined)
        VALUES (?, ?, ?, '', '', 0, 0, 1, ?)
        ''', 
        (username, email, password, datetime.datetime.now().isoformat()),
        commit=True
    )
    
    user = execute_with_retry(
        'SELECT id FROM auth_user WHERE username = ?', 
        (username,), 
        fetchone=True
    )
    user_id = user['id']
    execute_with_retry(
        '''
        INSERT INTO financeapp_userprofile (user_id, phone)
        VALUES (?, ?)
        ''', 
        (user_id, phone),
        commit=True
    )
    return jsonify({'message': 'User registered successfully!'}), 201

@app.route('/api/dashboard', methods=['GET'])
@token_required
def dashboard(current_user):
    user_id = request.args.get('user_id', current_user)
    
    transactions = execute_with_retry(
        'SELECT * FROM financeapp_transaction WHERE user_id = ?', 
        (user_id,), 
        fetchall=True
    )
    
    total_amount = sum(t['amount'] for t in transactions)
    total_upi = sum(t['amount'] for t in transactions if t['payment_method'] == 'UPI')
    total_cash = sum(t['amount'] for t in transactions if t['payment_method'] == 'Cash')
    
    return jsonify({
        'total_amount': total_amount,
        'total_upi': total_upi,
        'total_cash': total_cash
    })

@app.route('/api/transactions', methods=['GET'])
@token_required
def get_transactions(current_user):
    user_id = request.args.get('user_id', current_user)
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    search_term = request.args.get('search_term', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    transaction_type = request.args.get('transaction_type', '')
    
    query = 'SELECT * FROM financeapp_transaction WHERE user_id = ?'
    params = [user_id]
    if search_term:
        query += ' AND (category LIKE ? OR description LIKE ?)'
        params.extend(['%' + search_term + '%', '%' + search_term + '%'])
    
    if start_date:
        query += ' AND date >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND date <= ?'
        params.append(end_date)
    
    if transaction_type:
        query += ' AND transaction_type = ?'
        params.append(transaction_type)
    
    count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
    total_count = execute_with_retry(count_query, params, fetchone=True)[0]
    query += ' ORDER BY date DESC LIMIT ? OFFSET ?'
    offset = (page - 1) * per_page
    params.extend([per_page, offset])
    transactions = execute_with_retry(query, params, fetchall=True)
    transaction_list = []
    for t in transactions:
        transaction_list.append({
            'id': t['id'],
            'date': t['date'],
            'category': t['category'],
            'amount': t['amount'],
            'payment_method': t['payment_method'],
            'description': t['description'],
            'transaction_type': t['transaction_type']
        })
    
    total_pages = (total_count + per_page - 1) // per_page
    
    return jsonify({
        'transactions': transaction_list,
        'total_pages': total_pages,
        'current_page': page,
        'total_count': total_count
    })

@app.route('/api/transactions/<int:transaction_id>', methods=['GET'])
@token_required
def get_transaction(current_user, transaction_id):
    transaction = execute_with_retry(
        'SELECT * FROM financeapp_transaction WHERE id = ?', 
        (transaction_id,), 
        fetchone=True
    )
    
    if not transaction:
        return jsonify({'message': 'Transaction not found!'}), 404
    
    return jsonify({
        'id': transaction['id'],
        'date': transaction['date'],
        'category': transaction['category'],
        'amount': transaction['amount'],
        'payment_method': transaction['payment_method'],
        'description': transaction['description'],
        'transaction_type': transaction['transaction_type']
    })

@app.route('/api/transactions', methods=['POST'])
@token_required
def add_transaction(current_user):
    data = request.json
    
    if not data or not all(k in data for k in ['date', 'category', 'amount', 'payment_method', 'transaction_type']):
        return jsonify({'message': 'Missing required fields!'}), 400
    
    user_id = data.get('user_id', current_user)
    date = data.get('date')
    category = data.get('category')
    amount = data.get('amount')
    payment_method = data.get('payment_method')
    description = data.get('description', '')
    transaction_type = data.get('transaction_type')
    execute_with_retry(
        '''
        INSERT INTO financeapp_transaction (user_id, date, category, amount, payment_method, description, transaction_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', 
        (user_id, date, category, amount, payment_method, description, transaction_type),
        commit=True
    )
    transaction = execute_with_retry(
        'SELECT id FROM financeapp_transaction WHERE user_id = ? ORDER BY id DESC LIMIT 1', 
        (user_id,), 
        fetchone=True
    )
    
    transaction_id = transaction['id']
    
    return jsonify({'id': transaction_id, 'message': 'Transaction added successfully!'}), 201

@app.route('/api/transactions/<int:transaction_id>', methods=['PUT'])
@token_required
def update_transaction(current_user, transaction_id):
    data = request.json
    
    if not data:
        return jsonify({'message': 'No data provided!'}), 400
    
    transaction = execute_with_retry(
        'SELECT * FROM financeapp_transaction WHERE id = ?', 
        (transaction_id,), 
        fetchone=True
    )
    
    if not transaction:
        return jsonify({'message': 'Transaction not found!'}), 404
    date = data.get('date', transaction['date'])
    category = data.get('category', transaction['category'])
    amount = data.get('amount', transaction['amount'])
    payment_method = data.get('payment_method', transaction['payment_method'])
    description = data.get('description', transaction['description'])
    transaction_type = data.get('transaction_type', transaction['transaction_type'])
    
    execute_with_retry(
        '''
        UPDATE financeapp_transaction
        SET date = ?, category = ?, amount = ?, payment_method = ?, description = ?, transaction_type = ?
        WHERE id = ?
        ''', 
        (date, category, amount, payment_method, description, transaction_type, transaction_id),
        commit=True
    )
    
    return jsonify({'message': 'Transaction updated successfully!'})

@app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
@token_required
def delete_transaction(current_user, transaction_id):
    transaction = execute_with_retry(
        'SELECT * FROM financeapp_transaction WHERE id = ?', 
        (transaction_id,), 
        fetchone=True
    )
    
    if not transaction:
        return jsonify({'message': 'Transaction not found!'}), 404
    
    execute_with_retry(
        'DELETE FROM financeapp_transaction WHERE id = ?', 
        (transaction_id,),
        commit=True
    )
    
    return '', 204

@app.route('/api/statistics', methods=['GET'])
@token_required
def get_statistics(current_user):
    user_id = request.args.get('user_id', current_user)
    
    conn = get_db_connection()
    transactions = conn.execute('SELECT * FROM financeapp_transaction WHERE user_id = ?', (user_id,)).fetchall()
    conn.close()
    
    expenses = [t for t in transactions if t['transaction_type'] == 'Expense']
    income = [t for t in transactions if t['transaction_type'] == 'Income']
    
    total_expenses = sum(t['amount'] for t in expenses)
    total_income = sum(t['amount'] for t in income)
    
    expense_by_category = {}
    for t in expenses:
        category = t['category']
        expense_by_category[category] = expense_by_category.get(category, 0) + t['amount']
    
    income_by_category = {}
    for t in income:
        category = t['category']
        income_by_category[category] = income_by_category.get(category, 0) + t['amount']
    
    # Get top 5 spending categories
    top_spending_categories = dict(sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True)[:5])
    top_income_categories = dict(sorted(income_by_category.items(), key=lambda x: x[1], reverse=True)[:5])
    
    return jsonify({
        'total_expenses': total_expenses,
        'total_income': total_income,
        'expense_by_category': expense_by_category,
        'income_by_category': income_by_category,
        'top_spending_categories': top_spending_categories,
        'top_income_categories': top_income_categories
    })

@app.route('/api/statistics/daily', methods=['GET'])
@token_required
def daily_spending_data(current_user):
    user_id = request.args.get('user_id', current_user)
    
    conn = get_db_connection()
    transactions = conn.execute('SELECT date, SUM(amount) as total FROM financeapp_transaction WHERE user_id = ? GROUP BY date ORDER BY date', (user_id,)).fetchall()
    conn.close()
    
    labels = [t['date'] for t in transactions]
    amounts = [t['total'] for t in transactions]
    
    return jsonify({'labels': labels, 'amounts': amounts})

@app.route('/api/statistics/monthly', methods=['GET'])
@token_required
def monthly_spending_data(current_user):
    user_id = request.args.get('user_id', current_user)
    
    conn = get_db_connection()
    transactions = conn.execute('SELECT * FROM financeapp_transaction WHERE user_id = ?', (user_id,)).fetchall()
    conn.close()
    
    monthly_data = {}
    for t in transactions:
        date_obj = datetime.datetime.strptime(t['date'], '%Y-%m-%d')
        key = date_obj.strftime('%Y-%m')
        monthly_data[key] = monthly_data.get(key, 0) + t['amount']
    
    labels = [datetime.datetime.strptime(k, '%Y-%m').strftime('%b %Y') for k in monthly_data.keys()]
    amounts = list(monthly_data.values())
    
    return jsonify({'labels': labels, 'amounts': amounts})

# OCR endpoints
@app.route('/api/ocr/process', methods=['POST'])
@token_required
def process_receipt(current_user):
    if 'receipt' not in request.files:
        return jsonify({'message': 'No file part!'}), 400
    
    file = request.files['receipt']
    if file.filename == '':
        return jsonify({'message': 'No selected file!'}), 400
    
    # Save the file temporarily
    filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filename)
    
    # Process the image with OCR
    try:
        # Read the image
        img = cv2.imread(filename)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply thresholding
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        
        # Perform OCR
        text = pytesseract.image_to_string(thresh)
        
        # Extract information from the OCR text
        date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}'
        amount_pattern = r'(?:total|amount|amt)(?:\s*:)?\s*(?:rs\.?|₹)?\s*(\d+(?:\.\d{1,2})?)'
        
        # Find date
        date_match = re.search(date_pattern, text, re.IGNORECASE)
        date = date_match.group(0) if date_match else None
        
        # Find amount
        amount_match = re.search(amount_pattern, text, re.IGNORECASE)
        amount = amount_match.group(1) if amount_match else None
        
        # Try to determine category based on keywords
        categories = {
            "Food": ["restaurant", "cafe", "food", "meal", "lunch", "dinner", "breakfast"],
            "Entertainment": ["movie", "cinema", "theatre", "concert", "show"],
            "Utilities": ["electricity", "water", "gas", "bill", "utility"],
            "Travel": ["travel", "flight", "train", "bus", "taxi", "uber"],
            "Shopping": ["mall", "store", "shop", "purchase", "buy"],
            "Groceries": ["grocery", "supermarket", "market", "fruit", "vegetable"]
        }
        
        detected_category = "Other"
        for category, keywords in categories.items():
            if any(keyword in text.lower() for keyword in keywords):
                detected_category = category
                break
        
        receipt_info = {
            'date': date,
            'amount': amount,
            'category': detected_category,
            'text': text
        }
        
        # Clean up
        os.remove(filename)
        
        return jsonify({'receipt_info': receipt_info})
    
    except Exception as e:
        # Clean up in case of error
        if os.path.exists(filename):
            os.remove(filename)
        return jsonify({'message': f'Error processing receipt: {str(e)}'}), 500

@app.route('/api/ocr/save', methods=['POST'])
@token_required
def save_receipt_data(current_user):
    data = request.json
    
    if not data or not all(k in data for k in ['date', 'amount', 'category']):
        return jsonify({'message': 'Missing required fields!'}), 400
    
    user_id = data.get('user_id', current_user)
    date = data.get('date')
    category = data.get('category')
    amount = data.get('amount')
    description = data.get('description', 'Receipt OCR')
    payment_method = data.get('payment_method', 'Card')  # Default to Card
    transaction_type = 'Expense'  # Receipts are typically expenses
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO financeapp_transaction (user_id, date, category, amount, payment_method, description, transaction_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, date, category, amount, payment_method, description, transaction_type))
    
    transaction_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'id': transaction_id, 'message': 'Receipt data saved successfully!'}), 201

if __name__ == '__main__':
    app.run(debug=True)
