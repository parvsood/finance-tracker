import re
import cv2
import numpy as np
from django.shortcuts import render, redirect
from .models import Receipt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from financeapp.models import Transaction
from PIL import Image
from dateutil import parser as date_parser
from django.shortcuts import get_object_or_404
from .forms import ReceiptForm, ReceiptEditForm, ReceiptUploadOnlyForm
import pytesseract

CATEGORY_KEYWORDS = {
    'Food': [
        'burger', 'pizza', 'chips', 'soft drink', 'fries', 'noodles', 'sandwich', 'takatak',
        'coffee', 'tea', 'momos', 'wrap', 'roll', 'biryani', 'curry', 'ice cream', 'soda', 'paneer', 'thali', 'paratha', 'naan', 'gravy'
    ],
    'Grocery': [
        'milk', 'bread', 'rice', 'apple', 'banana', 'oil', 'flour', 'sugar', 'salt', 'atta',
        'dal', 'besan', 'butter', 'cheese', 'paneer', 'jam', 'chocolate', 'juice', 'vegetable', 'fruit', 'eggs'
    ],
    'Toiletries': [
        'soap', 'shampoo', 'toothpaste', 'tissue', 'detergent', 'lotion', 'deodorant',
        'toothbrush', 'face wash', 'handwash', 'shaving cream', 'razor', 'sanitary'
    ],
    'Stationery': [
        'pen', 'pencil', 'notebook', 'eraser', 'marker', 'paper', 'highlighter', 'stapler',
        'file', 'folder', 'tape', 'glue', 'sticky notes'
    ],
    'Electronics': [
        'charger', 'earphones', 'usb', 'cable', 'battery', 'adapter', 'mouse', 'keyboard',
        'power bank', 'headphones', 'monitor', 'tv', 'remote', 'speaker'
    ],
    'Clothing': [
        'shirt', 'jeans', 'socks', 'jacket', 't-shirt', 'pants', 'kurta', 'sweater',
        'hoodie', 'dress', 'skirt', 'top', 'leggings', 'scarf', 'cap'
    ],
    'Utilities': [
        'electricity', 'water', 'internet', 'phone bill', 'recharge', 'gas', 'mobile bill',
        'broadband', 'wifi', 'dth'
    ],
    'Entertainment': [
        'movie', 'concert', 'ticket', 'subscription', 'netflix', 'spotify', 'hotstar',
        'zee5', 'game', 'app', 'book', 'theatre'
    ],
    'Transport': [
        'uber', 'ola', 'taxi', 'bus', 'train', 'auto', 'flight', 'cab', 'metro', 'fare', 'ticket'
    ],
    'Healthcare': [
        'medicine', 'tablet', 'capsule', 'syrup', 'ointment', 'doctor', 'clinic', 'hospital',
        'consultation', 'prescription'
    ],
    'Fitness': [
        'gym', 'subscription', 'membership', 'lift', 'fitness', '1-year', 'training'
    ]
}

def categorize_item(item_name):
    item_name = item_name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in item_name for keyword in keywords):
            return category
    return 'Others'

def infer_payment_method(ocr_text):
    text = ocr_text.lower()
    if 'upi' in text:
        return 'UPI'
    elif 'cash' in text:
        return 'Cash'
    return 'UPI'

def extract_key_value_pairs(ocr_lines):
    key_value_pairs = {}
    for line in ocr_lines:
        match = re.search(r'(-?\d+\.?\d{0,2})\s*$', line)
        if match:
            amount = match.group(1)
            label = line[:match.start()].strip()
            if label:
                key_value_pairs[label.lower()] = float(amount)
    return key_value_pairs

def extract_receipt_info(ocr_text):
    item_pattern = r"(?:(\d+)\s*[xX*]\s*)?([A-Za-z\s]+?)\s+([\d,.]+)"
    lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]

    store_name = "Unknown Store"
    ignore_keywords = ["invoice", "bill", "balance", "date", "due", "terms", "project", "to", "amount"]

    for line in lines[:10]:
        lower_line = line.lower()
        if any(keyword in lower_line for keyword in ignore_keywords):
            continue
        if re.search(r'inv[\s\-:]?\d+', lower_line):
            continue
        if not line.isdigit() and 1 <= len(line.split()) <= 5:
            if line[0].isupper():
                store_name = line
                break

    total_matches = []
    priorities = {
        'grand total': 4,
        'bill total': 3,
        'total amount': 3,
        'amount due': 2,
        'total': 1,
        'sub total': 0
    }

    for i, line in enumerate(lines):
        for label, score in priorities.items():
            if label in line.lower():
                match = re.search(r'([₹$%]?\s*[\d]+[,.]?\d*)', line)
                if not match and i + 1 < len(lines):
                    match = re.search(r'([₹$%]?\s*[\d]+[,.]?\d*)', lines[i + 1])
                if match:
                    try:
                        amount = float(match.group(1).replace(',', '').replace('₹', '').replace('$', '').replace('%', ''))
                        total_matches.append((score, label, amount))
                    except ValueError:
                        continue

    total_amount = max(total_matches, key=lambda x: (x[0], x[2]))[2] if total_matches else 0.0
    date = None
    date_patterns = [
        r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
        r"\d{4}[/-]\d{1,2}[/-]\d{1,2}",
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}",
        r"\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?,?\s+\d{4}",
        r"\d{1,2}[a-zA-Z]+\s*\d{4}",
        r"\d{2}-\d{2}-\d{2,4}",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            try:
                parsed_date = date_parser.parse(match.group(), fuzzy=True)
                date = parsed_date.date()
                break
            except:
                continue

    items = []
    fallback_category = categorize_item(ocr_text)

    for match in re.finditer(item_pattern, ocr_text):
        quantity = int(match.group(1)) if match.group(1) else 1
        item_name = match.group(2).strip()
        price = float(match.group(3).replace(',', ''))

        items.append({
            'name': item_name,
            'quantity': quantity,
            'price': price,
            'category': categorize_item(item_name)
        })

    return {
        'total_amount': total_amount,
        'store_name': store_name,
        'date': date,
        'items': items,
        'category': fallback_category
    }

def preprocess_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Could not load image")

    max_height = 1200
    height, width = img.shape[:2]
    if height > max_height:
        scale = max_height / height
        img = cv2.resize(img, (int(width * scale), max_height), interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    coords = np.column_stack(np.where(gray > 0))
    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    center = (width // 2, height // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(img, M, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

    return deskewed

@login_required
def edit_receipt(request, receipt_id):
    receipt = get_object_or_404(Receipt, id=receipt_id)

    if request.method == 'POST':
        form = ReceiptForm(request.POST, request.FILES, instance=receipt)
        if form.is_valid():
            form.save()
            messages.success(request, 'Receipt updated successfully.')
            return redirect('transactions')
        else:
            messages.error(request, 'There was an error in your form.')
    else:
        form = ReceiptForm(instance=receipt)

    return render(request, 'edit_receipt.html', {'form': form, 'receipt': receipt})

@login_required
def upload_receipt(request):
    if request.method == "POST":
        form = ReceiptUploadOnlyForm(request.POST, request.FILES)
        if form.is_valid():
            receipt = form.save(commit=False)
            receipt.user = request.user
            receipt.save()

            if receipt.receipt_image:
                image = Image.open(receipt.receipt_image)
                text = pytesseract.image_to_string(image)

                if not text.strip():
                    messages.error(request, "OCR failed. Please upload a clearer image.")
                    return redirect('upload_receipt')
                receipt_info = extract_receipt_info(text)
                total_amount = receipt_info['total_amount']
                store_name = receipt_info['store_name']
                date = receipt_info['date']
                category = receipt_info['items'][0]['category'] if receipt_info['items'] else receipt_info['category']
                payment_method = infer_payment_method(text)
                return render(request, 'edit_receipt_info.html', {
                    'receipt': receipt,
                    'ocr_data': {
                        'store_name': store_name,
                        'date': date,
                        'total_amount': total_amount,
                        'category': category,
                        'payment_method': payment_method,
                        'description': f"Receipt from {store_name}",
                        'items': receipt_info['items'],
                    },
                    'form': ReceiptEditForm(),
                    'receipt_image': receipt.receipt_image.url
                })
        else:
            messages.error(request, "Invalid form data.")
            return redirect('upload_receipt')

    else:
        form = ReceiptUploadOnlyForm()

    return render(request, 'upload_receipt.html', {'form': form})


from django.views.decorators.csrf import csrf_exempt

@login_required
@csrf_exempt
def save_receipt_data(request):
    if request.method == 'POST':
        store_name = request.POST.get('store_name')
        date = request.POST.get('date')
        total_amount = request.POST.get('total_amount')
        category = request.POST.get('category')
        payment_method = request.POST.get('payment_method')
        description = request.POST.get('description')
        
        from django.db import transaction
        
        # Use transaction to prevent database locking
        with transaction.atomic():
            Transaction.objects.create(
                user=request.user,
                amount=total_amount,
                category=category,
                date=date,
                description=description or f"Receipt from {store_name}",
                payment_method=payment_method,
                transaction_type="Expense"
            )

        messages.success(request, "Transaction saved successfully.")
        return redirect('transactions')
    else:
        messages.error(request, "Invalid request.")
        return redirect('upload_receipt')
