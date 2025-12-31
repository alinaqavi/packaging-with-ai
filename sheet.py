import base64
import requests 
import re
from datetime import datetime
from flask_cors import CORS
from google import genai 
from google.genai.errors import APIError
from pdf2image import convert_from_bytes
from io import BytesIO
from flask import Flask, request, jsonify
from PIL import Image
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import traceback
from flask import Flask, request, render_template, redirect, url_for
import os
import google.auth.transport.requests
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.http
import json
from io import BytesIO
from datetime import datetime 

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# =========================================================================
# 🚨 CONFIGURATION 🚨
# =========================================================================
API_KEY = os.environ.get("GEMINI_API_KEY") 
# Using the same image endpoint you had in your file
GEMINI_IMAGE_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent"

# ✅ UPDATE THESE IDs / FILE PATHS if needed
GOOGLE_FOLDER_ID = "1uWCSerZoJteQVgvjtjMRikCc_IgIqQkl"
GOOGLE_SHEET_ID = "1uMT30zo01MNDwNEqE86HB7TTGhiqT9Q6prNyaXSBvAA"
SERVICE_ACCOUNT_FILE = "service-account-key.json"

# Flask Setup
app = Flask(__name__)
CORS(app) 
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB for uploads

# Initialize Gemini Client (text chat)
chat_client = None
if API_KEY:
    try:
        chat_client = genai.Client(api_key=API_KEY)
        print("✅ Gemini SDK client initialized.")
    except Exception as e:
        print(f"❌ Error initializing Gemini: {e}")
else:
    print("❌ GEMINI_API_KEY not found!")

# Initialize Google Services (Drive & Sheets)
drive_service = None
sheets_service = None

try:
    SCOPES = [
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/spreadsheets'
    ]
    
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    drive_service = build('drive', 'v3', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    print("✅ Google Drive & Sheets services initialized.")
except Exception as e:
    print(f"❌ Google Services initialization failed: {e}")

# =========================================================================
# AUTO-CREATE DRIVE FOLDER
# =========================================================================
def get_or_create_drive_folder():
    """Create Drive folder automatically if not exists."""
    global GOOGLE_FOLDER_ID
    
    if not drive_service:
        print("❌ Drive service not available")
        return None
    
    try:
        # Search for existing folder
        query = "name='Packaging App Logos' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, webViewLink)'
        ).execute()
        
        folders = results.get('files', [])
        
        if folders:
            GOOGLE_FOLDER_ID = folders[0]['id']
            print(f"✅ Using existing folder: {folders[0]['name']} (ID: {GOOGLE_FOLDER_ID})")
            return GOOGLE_FOLDER_ID
        
        # Create new folder
        folder_metadata = {
            'name': 'Packaging App Logos',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = drive_service.files().create(
            body=folder_metadata,
            fields='id, webViewLink'
        ).execute()
        
        GOOGLE_FOLDER_ID = folder.get('id')
        
        # Make folder publicly readable
        drive_service.permissions().create(
            fileId=GOOGLE_FOLDER_ID,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        print(f"✅ Created new folder: {folder.get('webViewLink')}")
        print(f"📁 Folder ID: {GOOGLE_FOLDER_ID}")
        return GOOGLE_FOLDER_ID
        
    except Exception as e:
        print(f"❌ Folder creation error: {e}")
        return None

# Initialize folder on startup
if drive_service:
    get_or_create_drive_folder()

# =========================================================================
# PRODUCT MAPPING
# =========================================================================
PRODUCT_MAP = {
    "paper_cup": "static/Paper_Cup.jpeg",
    "paper_bag": "static/Paper_Bag.webp", 
    "paper_bowl": "static/Paper_Bowl.jpg",
    "wrapping_paper": "static/wrapping_paper.jpg",
    "paper_napkin": "static/paper_napkin.jpg",
    "Meal_Box": "static/Meal_Box.png",
    "single_wall": "static/Single_wall_cup.jpeg",
    "double_wall": "static/Double_wall_cup.jpeg", 
    "flat": "static/White_Paper_Bag_Flat.png",
    "white_twisted": "static/White_Paper_Bag_Twisted.png",
    "twisted": "static/Paper_Bag_Twist.webp",
    "with_lid": "static/Paper_Bowl_Lid.jpg",
    "without_lid": "static/Paper_Bowl_NoLid.jpg",
    "pizza_box": "static/pizza_box.jpeg",
    "white_pizza_box": "static/white_pizza_box.jpeg",
    "triangular_pizza_box": "static/triangular_pizza_box.jpeg",
    "burger_box": "static/burger_box.jpeg",
    "sandwich_box": "static/sandwich_box.png",
    "sandwich_box2": "static/sandwich_box2.png",
    "roll_box": "static/roll_box.png",
    "roll_locking_box": "static/roll_locking_box.png",
    "roll_sliding_box": "static/roll_sliding_box.png",
    "noodle_pasta_box": "static/noodle_pasta_box.png",
    "popcorn_holder": "static/popcorn_holder.jpeg",
    "popcorn_holder2": "static/popcorn_holder2.png",
    "paper_tray": "static/paper_tray.png",
    "white_paper_stand_up_bag": "static/white_paper_stand_up_bag.png",
    "paper_stand_up_bag": "static/paper_stand_up_bag.png"
}

# =========================================================================
# ✅ PRODUCT-SPECIFIC PROMPTS
# =========================================================================
PRODUCT_PROMPTS = {
    # (Your existing templates — unchanged)
    "paper_bag": "Generate a full, highly realistic packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic on the center-front face of the standing paper shopping bag. Generate and apply complementary design elements, lines, or subtle repeating patterns based on the style of the uploaded logo and the product's function, across the visible surface areas of the bag to create a complete, branded look. {COLOR_RULE} The logo and design must be applied with realistic lighting and shadows. The background environment of the mockup should remain unchanged.",
    "flat": "Generate a full, highly realistic packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic on the center-front face of the standing paper shopping bag. Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns onto the side panels of the bag, inspired by the style of the logo or the product's function, to create a complete, branded look. {COLOR_RULE} The logo and design must be applied with realistic lighting and shadows. The background environment of the mockup should remain unchanged.",
    "white_twisted": "Generate a full, highly realistic packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic on the center-front face of the standing paper shopping bag. Generate and apply complementary design elements, lines, or subtle repeating patterns based on the style of the uploaded logo and the product's function, across the visible surface areas of the bag to create a complete, branded look. {COLOR_RULE} The logo and design must be applied with realistic lighting and shadows. The background environment of the mockup should remain unchanged.",
    "twisted": "Generate a full, highly realistic packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic on the center-front face of the standing paper shopping bag. Generate and apply complementary design elements, lines, or subtle repeating patterns based on the style of the uploaded logo and the product's function, across the visible surface areas of the bag to create a complete, branded look. {COLOR_RULE} The logo and design must be applied with realistic lighting and shadows. The background environment of the mockup should remain unchanged.",
    "wrapping_paper": "Apply the uploaded logo as a small to medium-sized, repeating pattern across the entire paper surface. The pattern must be scattered, non-overlapping, and uniformly spaced to ensure every logo is clean and readable. {COLOR_RULE}",
    "paper_napkin": "A highly realistic, top-down studio photograph of a neatly stacked pile of white paper napkins. Place the uploaded logo as a single, prominent graphic positioned perfectly in the center of the top napkin of the stack. The logo should conform realistically to the subtle texture and slight imperfections of the napkin, with natural shadows and lighting. {COLOR_RULE} The background environment of the mockup should remain unchanged.",
    "Meal_Box": "Generate a full, highly realistic takeout packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic centered on the top lid of the meal box. Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns onto the side panels of the box, inspired by the style of the logo or the product's function, to create a complete, branded look. {COLOR_RULE} The design must be realistically applied with texture, lighting, and shadows. The background environment of the mockup should remain unchanged.",
    "paper_bowl": "Generate a full, highly realistic disposable packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic on the exterior side of the paper bowl, conforming realistically to its curved surface. Generate and apply complementary design elements or graphic patterns around the main logo or on the rest of the bowl's exterior, inspired by the logo's style, to create a complete, branded look. {COLOR_RULE} The design must show appropriate lighting and shadows. The background environment of the mockup should remain consistent with the base product image.",
    "with_lid": "Generate a full, highly realistic disposable packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic on the exterior side of the paper bowl, conforming realistically to its curved surface. Generate and apply complementary design elements or graphic patterns around the main logo or on the rest of the bowl's exterior, inspired by the logo's style, to create a complete, branded look. {COLOR_RULE} The design must show appropriate lighting and shadows. The background environment of the mockup should remain consistent with the base product image.",
    "without_lid": "Generate a full, highly realistic disposable packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic on the exterior side of the paper bowl, conforming realistically to its curved surface. Generate and apply complementary design elements or graphic patterns around the main logo or on the rest of the bowl's exterior, inspired by the logo's style, to create a complete, branded look. {COLOR_RULE} The design must show appropriate lighting and shadows. The background environment of the mockup should remain consistent with the base product image.",
    "paper_cup": "Generate a full, highly realistic disposable beverage packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic centered on the front face of the cup. Generate and apply complementary design elements, patterns, or graphic lines onto the cup's surface, inspired by the logo's style, to complete the branded look. The design should conform realistically to the curved surface, displaying natural lighting, shadows, and subtle texture. {COLOR_RULE} The background environment of the mockup should remain unchanged.",
    "single_wall": "Generate a full, highly realistic disposable beverage packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic centered on the front face of the cup. Generate and apply complementary design elements, patterns, or graphic lines onto the cup's surface, inspired by the logo's style, to complete the branded look. The design should conform realistically to the curved surface, displaying natural lighting, shadows, and subtle texture. {COLOR_RULE} The background environment of the mockup should remain unchanged.",
    "double_wall": "Generate a full, highly realistic disposable beverage packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic centered on the front face of the cup. Generate and apply complementary design elements, patterns, or graphic lines onto the cup's surface, inspired by the logo's style, to complete the branded look. The design should conform realistically to the curved surface, displaying natural lighting, shadows, and subtle texture. {COLOR_RULE} The background environment of the mockup should remain unchanged.",
    "pizza_box": "Generate a full, highly realistic takeout packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic centered on the top lid of the pizza box. Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns onto the side panels of the box, inspired by the style of the logo or the product's function, to create a complete, branded look. {COLOR_RULE} The design must be realistically applied with texture, lighting, and shadows. The background environment of the mockup should remain unchanged.",
    "white_pizza_box": "Generate a full, highly realistic takeout packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic centered on the top lid of the white pizza box. Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns onto the side panels of the box, inspired by the style of the logo or the product's function, to create a complete, branded look. {COLOR_RULE} The design must be realistically applied with texture, lighting, and shadows. The background environment of the mockup should remain unchanged.",
    "triangular_pizza_box": "Generate a full, highly realistic takeout packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic centered on the top lid of the triangular pizza box. Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns onto the side panels of the box, inspired by the style of the logo or the product's function, to create a complete, branded look. {COLOR_RULE} The design must be realistically applied with texture, lighting, and shadows. The background environment of the mockup should remain unchanged.",
    "burger_box": "Generate a full, highly realistic takeout packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic centered on the top lid of the burger box. Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns onto the side panels of the box, inspired by the style of the logo or the product's function, to create a complete, branded look. {COLOR_RULE} The design must be realistically applied with texture, lighting, and shadows. The background environment of the mockup should remain unchanged.",
    "sandwich_box": "Generate a full, highly realistic takeout packaging studio mockup. Integrate the uploaded logo as a large, primary graphic centered on the top lid of the sandwich box. Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns onto the side panels of the box, inspired by the style of the logo or the product's function, to create a complete, branded look. {COLOR_RULE} The design must be realistically applied with texture, lighting, and shadows. The background environment of the mockup should remain unchanged.",
    "sandwich_box2": "Generate a full, highly realistic takeout packaging studio mockup. Integrate the uploaded logo as a large, primary graphic centered on the top lid of the sandwich box. Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns onto the side panels of the box, inspired by the style of the logo or the product's function, to create a complete, branded look. {COLOR_RULE} The design must be realistically applied with texture, lighting, and shadows. The background environment of the mockup should remain unchanged.",
    "roll_box": "Generate a full, highly realistic takeout packaging design studio mockup for a cylindrical roll box. Integrate the uploaded logo as a large, central branding element placed horizontally across the middle section of the roll box. Extend the design with complementary graphics, curved lines, and subtle texture patterns inspired by the logo's theme. {COLOR_RULE} Ensure the design wraps naturally around the curved surface of the roll box with proper highlights, shadows, and reflections for a professional, photo-realistic look. The background environment of the mockup should remain unchanged.",
    "roll_locking_box": "Generate a full, highly realistic takeout packaging design studio mockup for a rectangular roll locking box. Integrate the uploaded logo prominently on the top flap as the main branding element, centered and scaled for visibility. Extend complementary branding graphics across the front and side panels to give a cohesive branded appearance. {COLOR_RULE} The design must wrap naturally over the folds and locking flaps with accurate highlights, shadows, and paper texture for a professional, photo-realistic finish. The background environment of the mockup should remain unchanged.",
    "roll_sliding_box": "Generate a full, highly realistic takeout packaging design studio mockup for a rectangular roll sliding box with an inner tray partially pulled out. Apply the uploaded logo prominently on the outer sleeve, centered along the top surface. Extend complementary branding graphics along the sleeve sides and front edge for a cohesive branded appearance. {COLOR_RULE} Ensure the design wraps accurately over the sliding structure, showing depth, realistic shadows, reflections, and paper texture. The background environment of the mockup should remain unchanged.",
    "noodle_pasta_box": "Generate a full, ultra-realistic studio mockup of a takeout noodle or pasta box made from matte coated paperboard. Apply the uploaded logo prominently on the front panel as the main branding element. Extend complementary graphic patterns, curved lines, or thematic illustrations inspired by the logo and food category across the side and top panels for a cohesive branded design. {COLOR_RULE} Include realistic details such as fold lines, lid flaps, paper texture, and natural highlights for a premium photographic look. The background environment should remain minimal and unchanged.",
    "popcorn_holder": "Generate a full, highly realistic takeout packaging design studio mockup for a popcorn holder. Integrate the uploaded logo as a large, primary graphic centered on the front face of the popcorn holder. Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns onto the side panels and around the top rim of the holder, inspired by the style of the logo or the product's function. {COLOR_RULE} The design must be realistically applied with texture, lighting, and shadows, including the natural crinkling of paper. The background environment of the mockup should remain unchanged.",
    "popcorn_holder2": "Generate a full, highly realistic takeout packaging design studio mockup for a popcorn holder. Integrate the uploaded logo as a large, primary graphic centered on the front face of the popcorn holder. Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns onto the side panels and around the top rim of the holder, inspired by the style of the logo or the product's function. {COLOR_RULE} The design must be realistically applied with texture, lighting, and shadows, including the natural crinkling of paper. The background environment of the mockup should remain unchanged.",
    "paper_tray": "Generate a full, highly realistic takeout packaging design studio mockup for a rectangular paper food tray. Integrate the uploaded logo as a prominent graphic on the center of one of the long side panels of the tray. Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns onto the other side panels and possibly along the top rim, inspired by the style of the logo or the food product it might hold, to create a complete, branded look. {COLOR_RULE} The design must be realistically applied with texture, lighting, and shadows, including the natural folds and slight imperfections of paperboard. The background environment of the mockup should remain unchanged.",
    "white_paper_stand_up_bag": "Generate a full, highly realistic packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic on the center-front face of this standing white gift box, specifically on the solid panel above and/or around the transparent window. Generate and apply complementary design elements, lines, or subtle repeating patterns based on the style of the uploaded logo and the product's function, across the visible surface areas of the box, avoiding obscuring the transparent window, to create a complete, branded look. {COLOR_RULE} The logo and design must be applied with realistic lighting and shadows and appear integrated seamlessly with the box's texture. The background environment of the mockup should remain unchanged.",
    "paper_stand_up_bag": "Generate a full, highly realistic packaging design studio mockup. Integrate the uploaded logo as a large, primary graphic on the center-front face of the standing paper bag. Generate and apply complementary design elements, lines, or subtle repeating patterns based on the style of the uploaded logo and the product's function, across the visible surface areas of the bag to create a complete, branded look. {COLOR_RULE} The logo and design must be applied with realistic lighting and shadows and appear integrated seamlessly with the bag's texture. The background environment of the mockup should remain unchanged."
}

# =========================================================================
# HELPER FUNCTIONS
# =========================================================================

def upload_to_drive(file_data, filename, mime_type):
    """✅ Upload file to Google Drive and return shareable link."""
    if not drive_service or not GOOGLE_FOLDER_ID:
        print("⚠ Drive service or folder not initialized")
        return None
    
    try:
        print(f"🔧 Starting upload: {filename} ({mime_type}, {len(file_data)} bytes)")
        
        file_metadata = {
            'name': filename,
            'parents': [GOOGLE_FOLDER_ID]
        }
        
        media = MediaIoBaseUpload(
            BytesIO(file_data),
            mimetype=mime_type,
            resumable=True
        )
        
        print(f"📤 Uploading to Drive folder: {GOOGLE_FOLDER_ID}")
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink, webContentLink'
        ).execute()
        
        file_id = file.get('id')
        print(f"✅ File created with ID: {file_id}")
        
        # Make file publicly accessible
        try:
            drive_service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            print(f"✅ Public permission set")
        except Exception as perm_err:
            print(f"⚠ Permission setting failed: {perm_err}")
        
        link = file.get('webViewLink')
        print(f"✅ File uploaded successfully: {filename} → {link}")
        return link
        
    except Exception as e:
        print(f"❌ Drive upload error: {e}")
        traceback.print_exc()
        return None

def append_to_sheet(values):
    """✅ Append row to Sheet (A–G) with automatic timestamp in column A."""
    if not sheets_service:
        print("⚠ Sheets service not initialized")
        return False

    try:
        # Insert timestamp automatically
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_row = [timestamp] + values

        # Pad or trim to 7 columns total
        if len(full_row) < 7:
            full_row.extend([''] * (7 - len(full_row)))
        elif len(full_row) > 7:
            full_row = full_row[:7]

        body = {'values': [full_row]}
        result = sheets_service.spreadsheets().values().append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range='Sheet1!A:G',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()

        print(f"✅ Sheet updated at {timestamp}: {result.get('updates', {}).get('updatedRows', 0)} rows")
        return True

    except Exception as e:
        print(f"❌ Sheets append error: {e}")
        traceback.print_exc()
        return False


def convert_pdf_to_png(pdf_b64):
    """✅ Convert PDF to PNG (returns base64 PNG)."""
    try:
        print("📄 Converting PDF to PNG...")
        pdf_bytes = base64.b64decode(pdf_b64)
        images = convert_from_bytes(pdf_bytes, dpi=300)
        buffer = BytesIO()
        images[0].save(buffer, format="PNG")
        png_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        print(f"✅ PDF converted successfully (size: {len(png_b64)} chars)")
        return png_b64
    except Exception as e:
        print(f"❌ PDF conversion error: {e}")
        traceback.print_exc()
        raise

def convert_to_jpeg_if_unsupported(image_path):
    """Convert unsupported formats to JPEG and return (bytes, mime)."""
    file_extension = image_path.split('.')[-1].lower()
    
    if file_extension in ['jpeg', 'jpg', 'png']:
        with open(image_path, "rb") as f:
            data = f.read()
        return data, f"image/{'jpeg' if file_extension in ['jpg', 'jpeg'] else 'png'}"
    
    if file_extension in ['webp', 'avif']:
        print(f"⚠ Converting {file_extension} to JPEG")
        img = Image.open(image_path)
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        return buffer.getvalue(), "image/jpeg"
    
    raise ValueError(f"Unsupported format: {file_extension}")

def validate_uk_phone(phone):
    """Validate UK phone number."""
    phone_cleaned = re.sub(r'\s+', '', phone)
    uk_patterns = [
        r'^(\+44|0044)?7\d{9}$',
        r'^(\+44|0044)?[1-9]\d{9,10}$',
        r'^0[1-9]\d{8,9}$'
    ]
    return any(re.match(pattern, phone_cleaned) for pattern in uk_patterns)

def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# =========================================================================
# ROUTES
# =========================================================================

@app.route('/')
def index():
    return render_template('index.html')

# =========================================================================
# ✅ SMART CHATBOT: DESIGN CHAT + IMAGE EDIT + COMPANY INFO (PERFECTED)
# =========================================================================
@app.route('/send_chat', methods=['POST'])
def send_chat():
    """Smart chatbot that understands edit requests, company queries, and packaging design chat."""
    if not chat_client:
        return jsonify({"error": "AI services unavailable.", "message": "AI chatbot is currently offline. Please try again later."}), 200

    try:
        data = request.json or {}
        chat_history = data.get('history', [])
        product_name = data.get('product_name', 'packaging item')
        color = data.get('color', 'default color')
        image_b64 = data.get('image_b64') 
        image_mime = data.get('image_mime', 'image/png')

        user_message = ""
        if chat_history:
            for msg in reversed(chat_history):
                if msg.get('role') == 'user':
                    user_message = msg.get('content', '')
                    break

        print(f"📨 Chat request received | Product: {product_name} | Color: {color}")
        print(f"💬 User message: {user_message[:200]}")

        # ---------------------------------------------------------------------
        # 🧹 FIX: Reset chat history when a new product is selected
        # ---------------------------------------------------------------------
        last_product = None
        for msg in reversed(chat_history):
            if "Product:" in msg.get("content", ""):
                last_product = msg["content"].split("Product:")[-1].strip()
                break

        if last_product and last_product.lower() != product_name.lower():
            print(f"🧹 Product changed from {last_product} → {product_name}. Full chat reset triggered.")
            chat_history = []

            # 🧠 Fresh start for new product
            system_reset_message = f"Product changed: Now focusing only on {product_name}. Ignore all previous design prompts or instructions."
            user_message = system_reset_message

        # --- Intent Detection ---
        message_lower = user_message.lower()
        intent = "design_chat"
        
        # Keywords for image generation/instruction request (including common Hinglish/Hindi for robustness)
        image_request_keywords = ["generate", "create", "make", "image", "mockup", "photo", "mujhe", "karke do", "design karke do", "can you make", "how to make", "bana do", "tasveer bana"] 

        # Check for image edit intent 
        image_edit_keywords = ["shine", "gloss", "color", "matte", "texture", "background", "font", "text change", "make it", "change color", "make it shiny", "remove background", "pink", "blue", "red", "yellow", "metallic", "badal do", "rang", "chamak", "background hata do", "font badal", "edit", "modify"]
        
        # 🎯 PRIORITY 1: IMAGE EDIT (If there's an image AND user wants a change)
        if any(k in message_lower for k in image_edit_keywords) and image_b64:
            intent = "image_edit"
        
        # 🎯 PRIORITY 2: IMAGE GENERATION REQUEST (If user asks for creation without a base image)
        elif any(k in message_lower for k in image_request_keywords):
            intent = "image_request"
        
        # 🎯 PRIORITY 3: COMPANY INFO
        elif any(k in message_lower for k in ["company", "product", "service", "about", "who are you", "kitne product", "how many products", "aap kaun ho", "kaam kya hai"]):
            intent = "company_info"
        
        # 🎯 PRIORITY 4: OFF-TOPIC GUARDRAIL
        non_packaging_keywords = ['weather', 'news', 'movie', 'recipe', 'code', 'programming', 'math problem', 'homework', 'joke', 'story', 'game', 'politics', 'sports', 'celebrity', 'stock', 'cryptocurrency']
        if any(keyword in message_lower for keyword in non_packaging_keywords):
            response_text = "I specialize only in packaging design. Please ask questions related to your packaging design, colors, materials, branding, or mockup customization."
            return jsonify({"message": response_text})


        print(f"🎯 Detected intent: {intent}")

        # --- HANDLER 1: New Image Generation Request (Packify-Style Instructions) ---
        if intent == "image_request":
            instruction_reply = (
                "Absolutely! To **generate your custom packaging image**, please follow these steps using the user interface:\n"
                "1. **Select your Product** from the product list (e.g., Paper Cup, Pizza Box).\n"
                "2. **Choose a Color** or select the **'AI' button** near the color picker to get AI-suggested colors.\n"
                "3. **Upload your Logo** using the 'Upload Logo' button.\n"
                "4. Finally, press the **'Generate Mockup'** button to see your custom design!\n\n"
                "I cannot generate the image directly from the chat, but I'm here to guide you through the process and refine the design after generation."
            )
            return jsonify({"message": instruction_reply})

        # --- HANDLER 2: Image Edit Request ---
        elif intent == "image_edit":
            if not image_b64:
                 return jsonify({"message": "I need the current mockup image to apply your requested edit. Please upload a logo and generate a base mockup first."})
                 
            edit_prompt = f"Apply the following change to the existing packaging design: {user_message}"
            print(f"🪄 Image edit prompt: {edit_prompt}")

            # NOTE: This calls the placeholder function defined above. Ensure your actual logic is here.
            edited_image_data_url = image_edit_ai(edit_prompt, image_b64=image_b64, image_mime=image_mime)

            if not edited_image_data_url:
                # Failure response is professional and encourages retrying
                response_text = "I'm having trouble processing that specific image edit right now. Could you please try a simpler request, like 'make it glossy' or 'change background to white'?"
                return jsonify({"message": response_text})

            # Success: Return the new image data
            return jsonify({
                "message": f"Here is the updated **{product_name}** design with your requested change. Let me know if you need any further refinements!",
                "edited_image": edited_image_data_url, 
                "status": "image_updated"
            })

        # --- HANDLER 3: Company Info ---
        elif intent == "company_info":
            product_list = [name.replace('_', ' ').title() for name in PRODUCT_MAP.keys()]
            
            company_info = {
                "name": "Greenwich Packaging",
                "about": "We are Greenwich Packaging, a creative studio offering sustainable, customized branding and high-quality packaging mockups.",
                "services": ["Logo Printing", "3D Mockups", "Brand Strategy", "Packaging Consultation"]
            }

            if "product" in message_lower or "how many products" in message_lower:
                product_summary = f"{len(product_list)} unique packaging products. For example: {', '.join(product_list[:3])} and many more."
                reply = f"At **{company_info['name']}**, we offer {product_summary}. Which one are you interested in?"
            elif "service" in message_lower:
                reply = f"We offer services like: {', '.join(company_info['services'])}. Our focus is on bringing your brand to life."
            elif "about" in message_lower or "company" in message_lower:
                reply = company_info["about"]
            else:
                reply = f"We are **{company_info['name']}** — specialists in premium and eco-friendly packaging design and mockups."

            return jsonify({"message": reply})

        # --- HANDLER 4: Default Design Chat ---
        else:
            # System Instruction is the key to the 'Perfect' Packify-style tone.
            system_instruction = (
                "You are an expert AI Packaging Design Assistant for Greenwich Packaging. Follow these rules strictly:\n\n"
                "1. ONLY discuss packaging design, branding, colors, materials, printing, and customization.\n"
                "2. Keep responses concise (3-5 sentences maximum) and highly professional.\n"
                f"3. Current context: Product = {product_name}, Selected Color = {color}\n"
                "4. Ask clarifying questions about finish (matte/glossy), typography, or layout when needed.\n"
                "5. **Crucially, actively encourage the user to use the 'Generate Mockup' button to create a base design first. Then, instruct them that they can use the chat for instant live edits (e.g., 'make it glossy', 'change font to bold') to refine their design, acting as their seamless design partner.**"
            )

            contents = [
                genai.types.Content(
                    role='user' if msg['role'] == 'user' else 'model',
                    parts=[genai.types.Part.from_text(text=msg['content'])]
                )
                for msg in chat_history[-10:]
            ]
            
            if not contents or contents[-1].role != 'user' or contents[-1].parts[0].text != user_message:
                 contents.append(genai.types.Content(role='user', parts=[genai.types.Part.from_text(text=user_message)]))

            print(f"🤖 Sending to Gemini | Messages in context: {len(contents)}")
            print("🧠 Preparing to call Gemini model...")
            print(f"System instruction preview: {system_instruction[:120]}...")
            print(f"Last user message: {user_message[:120]}...")

            try:
                response = chat_client.models.generate_content(
                    model='gemini-2.5-flash', # Using a production model for better results
                    contents=contents,
                    config=dict(
                        system_instruction=system_instruction,
                        temperature=0.7,
                        max_output_tokens=250,
                        top_p=0.95,
                        top_k=40
                    )
                )

                if not response or not getattr(response, 'text', None):
                    print("⚠ Gemini returned no text or empty response:", response)
                    return jsonify({"message": "Sorry, I'm having trouble understanding that request. Please try again."})

                response_text = response.text.strip()
                print(f"✅ Response generated | Length: {len(response_text)} chars")
                return jsonify({"message": response_text})

            except Exception as e:
                print(f"❌ Gemini API Exception: {e}")
                traceback.print_exc()
                return jsonify({
                    "message": "I'm experiencing some issues connecting to the AI service. Please try again in a few seconds.",
                    "error": str(e)
                })

    except Exception as e:
        print(f"❌ Chat error: {e}")
        traceback.print_exc()
        return jsonify({
            "error": f"Chat service error: {str(e)}",
            "message": "Sorry, I'm experiencing technical difficulties. Please try again."
        }), 200


# =========================================================================
# 🖼 IMAGE EDIT HELPER - REAL GEMINI IMAGE API CALL (UNCHANGED)
# =========================================================================
def image_edit_ai(prompt, image_b64=None, image_mime="image/png"):
    """
    Call Gemini image API to edit an existing image using prompt.
    - prompt: textual instruction for edit
    - image_b64: base64 string of image to edit (without data:image/... prefix)
    - image_mime: mime type of image (e.g., image/png)
    Returns a data URL "data:image/png;base64,..." on success or None on failure.
    """
    try:
        print(f"🎨 image_edit_ai called | has_image={bool(image_b64)} | prompt_len={len(prompt)}")

        parts_list = []
        # Instruction text
        parts_list.append({"text": prompt})

        # If an image is provided, include it as inlineData so Gemini can edit it
        if image_b64:
            parts_list.append({
                "inlineData": {
                    "mimeType": image_mime,
                    "data": image_b64
                }
            })
        else:
             print("❌ image_edit_ai called without image data!")
             return None

        payload = {
            "contents": [{"parts": parts_list}],
            "generationConfig": {"responseModalities": ["IMAGE"]}
        }

        headers = {"Content-Type": "application/json"}
        # Call Gemini Image API
        resp = requests.post(
            GEMINI_IMAGE_API_URL,
            json=payload,
            headers=headers,
            params={"key": API_KEY},
            timeout=300
        )

        if resp.status_code != 200:
            try:
                err_json = resp.json()
                msg = err_json.get("error", {}).get("message", resp.text[:200])
            except Exception:
                msg = resp.text[:200]
            print(f"❌ Gemini image API error: HTTP {resp.status_code}: {msg}")
            return None

        result = resp.json()
        candidates = result.get("candidates", [])
        if not candidates:
            print("❌ No candidates returned by Gemini image API.")
            return None

        # Find inlineData in response
        first_candidate = candidates[0]
        parts = first_candidate.get("content", {}).get("parts", [])
        if not parts or "inlineData" not in parts[0]:
            # Safety filter block or unexpected response structure
            print("❌ inlineData missing in Gemini image response parts. Possibly blocked by safety filter.")
            return None

        img_b64 = parts[0]["inlineData"]["data"]
        # Return data URL so frontend can directly show it
        data_url = f"data:image/png;base64,{img_b64}"
        print(f"✅ Image edited successfully (size: {len(img_b64)} chars)")
        return data_url

    except Exception as e:
        print(f"❌ image_edit_ai exception: {e}")
        traceback.print_exc()
        return None

# =========================================================================
# ✅ MOCKUP GENERATION ROUTE (UNCHANGED)
# =========================================================================
@app.route("/generate_image", methods=["POST"])
def generate_mockup():
    """✅ Generate mockup WITH logo upload to Drive and applies selected color."""
    if not API_KEY:
        return jsonify({"error": "API Key missing."}), 500
            
    try:
        data = request.get_json(silent=True) 
        if data is None:
            return jsonify({"error": "Invalid data."}), 400

        main_product_id = data.get("product_name")
        sub_product_id = data.get("sub_product_id")
        product_id = sub_product_id if sub_product_id else main_product_id
        
        logo_b64 = data.get("logo_b64") 
        logo_mime_type = data.get("logo_mime_type")
        user_design_prompt = data.get("design_prompt", "").strip() 
        selected_color = data.get("color", "default color").strip()
        
        print(f"🎨 Mockup Generation Request:")
        print(f"   Product: main={main_product_id}, sub={sub_product_id}, final={product_id}")
        print(f"   Color: {selected_color}")
        print(f"   Logo: {bool(logo_b64)}")
        print(f"   Design Prompt: {user_design_prompt[:100] if user_design_prompt else 'None'}...")
        
        if not product_id:
            return jsonify({"error": "No product selected."}), 400
        
        # ✅ Handle PDF conversion
        original_mime_type = logo_mime_type
        if logo_b64 and logo_mime_type == "application/pdf":
            print("📄 Converting PDF logo to PNG...")
            logo_b64 = convert_pdf_to_png(logo_b64)
            logo_mime_type = "image/png"
        
        # ✅ Upload logo to Drive FIRST
        logo_drive_url = ""
        
        if logo_b64 and logo_mime_type:
            print(f"📁 Logo detected: mime_type={logo_mime_type}, data_length={len(logo_b64)}")
            
            try:
                logo_data = base64.b64decode(logo_b64)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Determine file extension based on ORIGINAL mime type
                ext_map = {
                    "image/png": "png",
                    "image/jpeg": "jpg",
                    "image/jpg": "jpg",
                    "application/pdf": "png"  # PDF converted to PNG
                }
                ext = ext_map.get(original_mime_type, "png")
                
                logo_filename = f"logo_{product_id}_{timestamp}.{ext}"
                
                print(f"📤 Uploading logo to Drive: {logo_filename} (size: {len(logo_data)} bytes)")
                
                # Upload with CURRENT mime type (after conversion)
                logo_drive_url = upload_to_drive(logo_data, logo_filename, logo_mime_type)
                
                if logo_drive_url:
                    # ✅ Log logo upload immediately
                    sheet_success = append_to_sheet([
                       "Logo Upload",
                        logo_filename,
                          "",
                        product_id,
                        logo_drive_url,
                       f"Color: {selected_color}, Original: {original_mime_type}"
])

                    print(f"✅ Logo uploaded & logged: {logo_drive_url} (Sheet: {sheet_success})")
                else:
                    print("⚠️ Logo upload to Drive failed - no URL returned")
                    
            except Exception as logo_error:
                print(f"❌ Logo upload error: {logo_error}")
                traceback.print_exc()
        else:
            print(f"ℹ️ No logo to upload: logo_b64={bool(logo_b64)}, mime_type={logo_mime_type}")

        # Get product image
        product_image_path = PRODUCT_MAP.get(product_id)
        
        if not product_image_path or not os.path.exists(product_image_path):
            print(f"❌ Product not found: {product_id}")
            return jsonify({"error": f"Product image not found: {product_id}"}), 400

        product_data, product_mime_type = convert_to_jpeg_if_unsupported(product_image_path)
        product_b64 = base64.b64encode(product_data).decode("utf-8")
        
        print(f"📦 Product image loaded: {product_image_path} ({product_mime_type})")
        
        # =====================================================================
        # ✅ COLOR INJECTION LOGIC
        # =====================================================================
        if selected_color and selected_color.lower() != 'none':
            color_rule = f"The primary material color of the packaging must be strictly changed to the hex color code {selected_color}."
        else:
            color_rule = "Keep the original packaging color or let AI choose an appropriate color based on the design."

        # ✅ Get product-specific prompt and inject the color rule
        base_prompt_template = PRODUCT_PROMPTS.get(product_id,
            f"Generate a photorealistic packaging mockup. Use the first image as base product. {color_rule}"
        )

        # Replace the {COLOR_RULE} placeholder with the actual instruction
        base_prompt = base_prompt_template.replace('{COLOR_RULE}', color_rule)
        
        # Construct final request prompt
        image_request_prompt = base_prompt
        
        if logo_b64:
            image_request_prompt += " Blend the second image (logo) naturally onto the product surface with realistic lighting and perspective."
        
        if user_design_prompt:
            image_request_prompt += f" Additional design requirements from user: {user_design_prompt}"
        
        print(f"🎯 Final prompt length: {len(image_request_prompt)} chars")
        
        # =====================================================================
        # Construct API payload
        # =====================================================================
        parts_list = []
        
        parts_list.append({"text": image_request_prompt})
        parts_list.append({
            "inlineData": {
                "mimeType": product_mime_type, 
                "data": product_b64
            }
        })
        
        if logo_b64:
            parts_list.append({
                "inlineData": {
                    "mimeType": logo_mime_type, 
                    "data": logo_b64
                }
            })
        
        payload = {
            "contents": [{"parts": parts_list}],
            "generationConfig": {"responseModalities": ["IMAGE"]} 
        }

        headers = {"Content-Type": "application/json"}
        
        print("🚀 Sending request to Gemini Image API...")
        
        response = requests.post(
            GEMINI_IMAGE_API_URL, 
            json=payload, 
            headers=headers, 
            params={"key": API_KEY}, 
            timeout=300 
        ) 
        
        if response.status_code != 200:
            error_details = f"HTTP {response.status_code}"
            try:
                error_json = response.json()
                error_details += f": {error_json.get('error', {}).get('message', 'Unknown')}"
            except:
                error_details += f": {response.text[:200]}"
            
            print(f"❌ Gemini API Error: {error_details}")
            return jsonify({"error": f"Mockup generation failed: {error_details}"}), 500

        result = response.json()
        candidates = result.get("candidates", [])
        
        if not candidates or "inlineData" not in candidates[0].get("content", {}).get("parts", [{}])[0]:
            safety_reason = "Image generation blocked by safety filters. Please try with different design requirements."
            print(f"❌ {safety_reason}")
            return jsonify({"error": safety_reason}), 500

        img_b64 = candidates[0]["content"]["parts"][0]["inlineData"]["data"]
        
        print(f"✅ Mockup generated successfully! Image size: {len(img_b64)} chars")
        
        # ✅ Log successful mockup generation
        append_to_sheet([
    "Mockup Generated",
    f"mockup_{product_id}.png",
    "",
    product_id,
    logo_drive_url if logo_drive_url else "No logo",
    f"Color: {selected_color}, Prompt: {user_design_prompt[:50] if user_design_prompt else 'Default'}"
])

        
        return jsonify({
            "image_b64": img_b64, 
            "message": "Mockup generated successfully!", 
            "logo_url": logo_drive_url
        })

    except Exception as e:
        print(f"❌ Mockup generation error: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# =========================================================================
# ✅ DOWNLOAD VERIFICATION ROUTE (UNCHANGED)
# =========================================================================
@app.route("/verify_download", methods=["POST"])
def verify_download():
    """✅ Verify user and store contact info."""
    try:
        data = request.get_json()
        email = data.get("email", "").strip()
        phone = data.get("phone", "").strip()
        
        print(f"📋 Download verification request: email={email}, phone={phone}")
        
        if not validate_email(email):
            print(f"❌ Invalid email: {email}")
            return jsonify({"error": "Invalid email address"}), 400
        
        if not validate_uk_phone(phone):
            print(f"❌ Invalid phone: {phone}")
            return jsonify({"error": "Invalid UK phone number"}), 400
        
        sheet_data = [
    "Download Request",
    email,
    phone,
    "Verified User",
    "",
    "Download verified successfully"
]

        
        if append_to_sheet(sheet_data):
            print(f"✅ Contact stored successfully: {email} | {phone}")
            return jsonify({
                "success": True,
                "message": "Verification successful! You can now download the mockup."
            })
        else:
            print("⚠️ Sheet append failed but allowing download")
            return jsonify({
                "success": True,
                "message": "Verification complete (offline mode)"
            })
        
    except Exception as e:
        print(f"❌ Verification error: {e}")
        traceback.print_exc()
        return jsonify({"error": "Verification failed. Please try again."}), 500

# =========================================================================
# ✅ HEALTH CHECK ROUTE (UNCHANGED)
# =========================================================================
@app.route("/health", methods=["GET"])
def health_check():
    """Check if all services are running properly."""
    status = {
        "api_key": bool(API_KEY),
        "chat_client": bool(chat_client),
        "drive_service": bool(drive_service),
        "sheets_service": bool(sheets_service),
        "folder_id": GOOGLE_FOLDER_ID,
        "timestamp": datetime.now().isoformat()
    }
    
    all_ok = all([status["api_key"], status["chat_client"]])
    
    return jsonify({
        "status": "healthy" if all_ok else "degraded",
        "services": status
    }), 200 if all_ok else 503

# =========================================================================
# ✅ ERROR HANDLERS (UNCHANGED)
# =========================================================================
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum size is 16MB"}), 413




@app.route('/send_chat', methods=['POST'])
def send_chat():
    """Smart chatbot that understands edit requests, company queries, and packaging design chat."""
    if not chat_client:
        return jsonify({"error": "AI services unavailable.", "message": "AI chatbot is currently offline. Please try again later."}), 200

    try:
        data = request.json or {}
        chat_history = data.get('history', [])
        product_name = data.get('product_name', 'packaging item')
        color = data.get('color', 'default color')
        image_b64 = data.get('image_b64') 
        image_mime = data.get('image_mime', 'image/png')

        user_message = ""
        if chat_history:
            for msg in reversed(chat_history):
                if msg.get('role') == 'user':
                    user_message = msg.get('content', '')
                    break

        print(f"📨 Chat request received | Product: {product_name} | Color: {color}")
        print(f"💬 User message: {user_message[:200]}")

        # ---------------------------------------------------------------------
        # 🧹 FIX: Reset chat history when a new product is selected
        # ---------------------------------------------------------------------
        last_product = None
        for msg in reversed(chat_history):
            if "Product:" in msg.get("content", ""):
                last_product = msg["content"].split("Product:")[-1].strip()
                break

        if last_product and last_product.lower() != product_name.lower():
            print(f"🧹 Product changed from {last_product} → {product_name}. Full chat reset triggered.")
            chat_history = []
            system_reset_message = f"Product changed: Now focusing only on {product_name}. Ignore all previous design prompts or instructions."
            user_message = system_reset_message

        # --- Intent Detection ---
        message_lower = user_message.lower()
        intent = "design_chat"
        
        image_request_keywords = ["generate", "create", "make", "image", "mockup", "photo", "mujhe", "karke do", "design karke do", "can you make", "how to make", "bana do", "tasveer bana"]
        image_edit_keywords = ["shine", "gloss", "color", "matte", "texture", "background", "font", "text change", "make it", "change color", "make it shiny", "remove background", "pink", "blue", "red", "yellow", "metallic", "badal do", "rang", "chamak", "background hata do", "font badal", "edit", "modify"]
        
        if any(k in message_lower for k in image_edit_keywords) and image_b64:
            intent = "image_edit"
        elif any(k in message_lower for k in image_request_keywords):
            intent = "image_request"
        elif any(k in message_lower for k in ["company", "product", "service", "about", "who are you", "kitne product", "how many products", "aap kaun ho", "kaam kya hai"]):
            intent = "company_info"
        
        non_packaging_keywords = ['weather', 'news', 'movie', 'recipe', 'code', 'programming', 'math problem', 'homework', 'joke', 'story', 'game', 'politics', 'sports', 'celebrity', 'stock', 'cryptocurrency']
        if any(keyword in message_lower for keyword in non_packaging_keywords):
            response_text = "I specialize only in packaging design. Please ask questions related to your packaging design, colors, materials, branding, or mockup customization."
            return jsonify({"message": response_text})

        print(f"🎯 Detected intent: {intent}")

        # --- HANDLER 1: New Image Generation Request ---
        if intent == "image_request":
            instruction_reply = (
                "Absolutely! To **generate your custom packaging image**, please follow these steps using the user interface:\n"
                "1. **Select your Product** from the product list (e.g., Paper Cup, Pizza Box).\n"
                "2. **Choose a Color** or select the **'AI' button** near the color picker to get AI-suggested colors.\n"
                "3. **Upload your Logo** using the 'Upload Logo' button.\n"
                "4. Finally, press the **'Generate Mockup'** button to see your custom design!\n\n"
                "I cannot generate the image directly from the chat, but I'm here to guide you through the process and refine the design after generation."
            )

            # ✅ Save chat summary
            # save_chat_session({
            #     "id": datetime.now().strftime("%Y%m%d%H%M%S"),
            #     "title": f"{product_name} - {datetime.now().strftime('%b %d')}",
            #     "messages": chat_history
            # })
            def save_chat_session(chat_history):
               with open("chat_history.json", "w") as f:
                 json.dump(chat_history, f, indent=2)

            return jsonify({"message": instruction_reply})

        # --- HANDLER 2: Image Edit Request ---
        elif intent == "image_edit":
            if not image_b64:
                return jsonify({"message": "I need the current mockup image to apply your requested edit. Please upload a logo and generate a base mockup first."})
            
            edit_prompt = f"Apply the following change to the existing packaging design: {user_message}"
            print(f"🪄 Image edit prompt: {edit_prompt}")
            edited_image_data_url = image_edit_ai(edit_prompt, image_b64=image_b64, image_mime=image_mime)

            if not edited_image_data_url:
                response_text = "I'm having trouble processing that specific image edit right now. Could you please try a simpler request, like 'make it glossy' or 'change background to white'?"
                return jsonify({"message": response_text})

            # ✅ Save chat summary
            save_chat_session({
                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                "title": f"{product_name} - {datetime.now().strftime('%b %d')}",
                "messages": chat_history
            })

            return jsonify({
                "message": f"Here is the updated **{product_name}** design with your requested change. Let me know if you need any further refinements!",
                "edited_image": edited_image_data_url, 
                "status": "image_updated"
            })

        # --- HANDLER 3: Company Info ---
        elif intent == "company_info":
            product_list = [name.replace('_', ' ').title() for name in PRODUCT_MAP.keys()]
            company_info = {
                "name": "Greenwich Packaging",
                "about": "We are Greenwich Packaging, a creative studio offering sustainable, customized branding and high-quality packaging mockups.",
                "services": ["Logo Printing", "3D Mockups", "Brand Strategy", "Packaging Consultation"]
            }

            if "product" in message_lower or "how many products" in message_lower:
                product_summary = f"{len(product_list)} unique packaging products. For example: {', '.join(product_list[:3])} and many more."
                reply = f"At **{company_info['name']}**, we offer {product_summary}. Which one are you interested in?"
            elif "service" in message_lower:
                reply = f"We offer services like: {', '.join(company_info['services'])}. Our focus is on bringing your brand to life."
            elif "about" in message_lower or "company" in message_lower:
                reply = company_info["about"]
            else:
                reply = f"We are **{company_info['name']}** — specialists in premium and eco-friendly packaging design and mockups."

            # ✅ Save chat summary
            save_chat_session({
                "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                "title": f"{product_name} - {datetime.now().strftime('%b %d')}",
                "messages": chat_history
            })
            return jsonify({"message": reply})

        # --- HANDLER 4: Default Design Chat ---
        else:
            system_instruction = (
                "You are an expert AI Packaging Design Assistant for Greenwich Packaging. Follow these rules strictly:\n\n"
                "1. ONLY discuss packaging design, branding, colors, materials, printing, and customization.\n"
                "2. Keep responses concise (3-5 sentences maximum) and highly professional.\n"
                f"3. Current context: Product = {product_name}, Selected Color = {color}\n"
                "4. Ask clarifying questions about finish (matte/glossy), typography, or layout when needed.\n"
                "5. **Encourage the user to use 'Generate Mockup' to create a base design first and then refine via chat edits.**"
            )

            contents = [
                genai.types.Content(
                    role='user' if msg['role'] == 'user' else 'model',
                    parts=[genai.types.Part.from_text(text=msg['content'])]
                )
                for msg in chat_history[-10:]
            ]

            if not contents or contents[-1].role != 'user' or contents[-1].parts[0].text != user_message:
                contents.append(genai.types.Content(role='user', parts=[genai.types.Part.from_text(text=user_message)]))

            print(f"🤖 Sending to Gemini | Messages in context: {len(contents)}")

            try:
                response = chat_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=contents,
                    config=dict(
                        system_instruction=system_instruction,
                        temperature=0.7,
                        max_output_tokens=250,
                        top_p=0.95,
                        top_k=40
                    )
                )

                if not response or not getattr(response, 'text', None):
                    return jsonify({"message": "Sorry, I'm having trouble understanding that request. Please try again."})

                response_text = response.text.strip()
                print(f"✅ Response generated | Length: {len(response_text)} chars")

                # ✅ Save chat summary
                save_chat_session({
                    "id": datetime.now().strftime("%Y%m%d%H%M%S"),
                    "title": f"{product_name} - {datetime.now().strftime('%b %d')}",
                    "messages": chat_history
                })

                return jsonify({"message": response_text})

            except Exception as e:
                print(f"❌ Gemini API Exception: {e}")
                traceback.print_exc()
                return jsonify({
                    "message": "I'm experiencing some issues connecting to the AI service. Please try again shortly.",
                    "error": str(e)
                })

    except Exception as e:
        print(f"❌ Chat error: {e}")
        traceback.print_exc()
        return jsonify({
            "error": f"Chat service error: {str(e)}",
            "message": "Sorry, I'm experiencing technical difficulties. Please try again."
        }), 200