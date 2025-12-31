# =========================================================================
# 🎨 ENHANCED VM BRANDING PDF GENERATION - MATCHING GUIDELINES
# =========================================================================
# This module replaces the generate_vm_sheet function in app.py
# It creates professional VM branding sheets following the Veggie Master guidelines

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from datetime import datetime
import os

# =========================================================================
# COLOR PALETTE (From VM Guidelines)
# =========================================================================
VM_COLORS = {
    'orange': HexColor('#FF6B35'),      # PANTONE 7579 C
    'green': HexColor('#00B050'),       # PANTONE 7481 C
    'black': HexColor('#1A1A1A'),       # Black
    'white': HexColor('#FFFFFF'),       # White
    'light_gray': HexColor('#F5F5F5'),  # Light background
    'dark_gray': HexColor('#333333'),   # Text
}

def generate_vm_sheet_enhanced(app, request, send_file, jsonify, traceback, PRODUCT_MAP, PRODUCT_PROMPTS, chat_client, requests as req, GEMINI_IMAGE_API_URL, API_KEY):
    """
    ✅ Generate Professional VM Sheet PDF matching branding guidelines
    
    Key Features:
    - Cover page with brand identity
    - Professional product mockup pages
    - Proper spacing and alignment per guidelines
    - Color-coded sections
    - Professional typography
    """
    
    # Product data structure
    allProducts = [
        { 
            'id': 'paper_cup', 
            'name': 'Paper Cup',
            'description': 'Premium quality single and double wall paper cups for hot and cold beverages. Available in multiple sizes with eco-friendly materials and custom branding options.',
            'subOptions': [
                {'id': 'single_wall', 'name': 'Single Wall Paper Cup'}, 
                {'id': 'double_wall', 'name': 'Double Wall Paper Cup'}
            ] 
        },
        { 
            'id': 'paper_bag', 
            'name': 'Paper Bag',
            'description': 'Eco-friendly kraft and white paper bags with twisted or flat handles. Perfect for retail, food service, and promotional use. Strong and durable construction.',
            'subOptions': [
                {'id': 'flat', 'name': 'White Flat Handle Paper Bag'}, 
                {'id': 'white_twisted', 'name': 'White Twisted Handle Paper Bag'},
                {'id': 'k_paper_bag_twisted', 'name': 'Kraft Twisted Handle Paper Bag'},
                {'id': 'k_paper_bag_flat', 'name': 'Kraft Flat Handle Paper Bag'}
            ] 
        },
        { 
            'id': 'paper_bowl', 
            'name': 'Paper Bowl',
            'description': 'Durable paper bowls suitable for soups, salads, noodles, and hot or cold food items. Leak-resistant coating and microwave safe. Available in multiple sizes.',
            'subOptions': [] 
        },
        { 
            'id': 'wrapping_paper', 
            'name': 'Food Wrapping Paper',
            'description': 'Custom printed greaseproof wrapping paper rolls for food service, retail packaging, and promotional wrapping. Available in kraft and white with custom prints.',
            'subOptions': [] 
        },
        { 
            'id': 'pizza_box', 
            'name': 'Pizza Box',
            'description': 'Premium corrugated pizza boxes in standard kraft, white, and triangular slice designs. Keeps pizza hot and fresh with ventilation holes. Custom printing available.',
            'subOptions': [
                {'id': 'pizza_box', 'name': 'Standard Kraft Pizza Box'},
                {'id': 'triangular_pizza_box', 'name': 'Triangular Slice Pizza Box'}, 
                {'id': 'white_pizza_box', 'name': 'White Pizza Box'}
            ] 
        },
        { 
            'id': 'burger_box', 
            'name': 'Burger Box',
            'description': 'Sturdy burger boxes with secure closure. Perfect for burgers, sandwiches, and hot food items. Grease-resistant material with excellent insulation.',
            'subOptions': [] 
        },
        { 
            'id': 'sandwich_box', 
            'name': 'Sandwich Box',
            'description': 'Triangular wedge-style sandwich boxes with clear windows for product visibility. Ideal for displaying fresh sandwiches, wraps, and deli items.',
            'subOptions': [
                {'id': 'sandwich_box', 'name': 'Window Sandwich Box'},
                {'id': 'sandwich_box2', 'name': 'Standard Sandwich Box'}
            ] 
        },
        { 
            'id': 'Meal_Box', 
            'name': 'Meal Box',
            'description': 'Multi-compartment meal boxes perfect for complete meals. Leak-proof design with secure locking mechanism. Suitable for hot and cold foods.',
            'subOptions': [] 
        },
        { 
            'id': 'roll_box', 
            'name': 'Roll Box',
            'description': 'Versatile roll-style boxes with locking and sliding mechanisms. Ideal for wraps, sandwiches, kebabs, and baked goods. Available in multiple sizes.',
            'subOptions': [
                {'id': 'roll_box', 'name': 'Standard Roll Box'},
                {'id': 'roll_locking_box', 'name': 'Roll Locking Box'}, 
                {'id': 'roll_sliding_box', 'name': 'Roll Sliding Box'}
            ] 
        },
        { 
            'id': 'noodle_pasta_box', 
            'name': 'Noodle Box',
            'description': 'Classic Asian-style noodle boxes perfect for noodles, pasta, rice dishes, and more. Leak-proof with convenient folding handle.',
            'subOptions': [] 
        },
        { 
            'id': 'popcorn_holder', 
            'name': 'Popcorn & Fries Holder',
            'description': 'Classic cinema-style popcorn holders and french fries containers. Fun and functional for events, cinemas, and food service.',
            'subOptions': [
                {'id': 'popcorn_holder', 'name': 'Popcorn Holder'},
                {'id': 'popcorn_holder2', 'name': 'Large Popcorn Holder'}, 
                {'id': 'fries_holder', 'name': 'French Fries Holder'}
            ] 
        },
        { 
            'id': 'paper_tray', 
            'name': 'Paper Tray',
            'description': 'Disposable paper food trays for serving snacks, appetizers, and fast food. Grease-resistant and sturdy construction.',
            'subOptions': [] 
        },
        { 
            'id': 'white_paper_stand_up_bag', 
            'name': 'Stand Up Pouch',
            'description': 'Premium stand-up pouches with or without windows. Perfect for coffee, tea, snacks, and dry goods. Resealable zip closure available.',
            'subOptions': [
                {'id': 'white_paper_stand_up_bag', 'name': 'White Stand Up Bag with Window'},
                {'id': 'paper_stand_up_bag', 'name': 'Kraft Stand Up Bag'}
            ] 
        },
        { 
            'id': 'k pastry box', 
            'name': 'Pastry Box & Holder',
            'description': 'Premium pastry boxes and holders for bakery items, cakes, and desserts. Available with handles and various opening styles for easy access.',
            'subOptions': [
                {'id': 'k pastry box', 'name': 'Kraft Pastry Box'},
                {'id': 'pastry_box_with_handle', 'name': 'Pastry Box with Handle'},
                {'id': 'k pastry holder', 'name': 'Kraft Pastry Holder'},
                {'id': 'pastry holder', 'name': 'Pastry Tray Holder'},
                {'id': 'pastry holder 2', 'name': 'Premium Pastry Holder'}
            ] 
        },
        { 
            'id': 'handle_cake_box', 
            'name': 'Cake Box',
            'description': 'Sturdy cake boxes with reinforced corners. Available with handles, windows, and various sizes for bakeries and special occasions.',
            'subOptions': [
                {'id': 'handle_cake_box', 'name': 'Cake Box with Handle'},
                {'id': 'cake_box', 'name': 'Standard Cake Box'},
                {'id': 'cake_box2', 'name': 'Window Cake Box'}
            ] 
        },
        { 
            'id': 'flat_box', 
            'name': 'Flat Box',
            'description': 'Versatile flat rectangular boxes perfect for takeaway meals, pastries, and general food packaging. Available in kraft and white.',
            'subOptions': [
                {'id': 'flat_box', 'name': 'White Flat Box'},
                {'id': 'flat_box2', 'name': 'Kraft Flat Box'}
            ] 
        },
        { 
            'id': 'Biryani_box2', 
            'name': 'Biryani Box',
            'description': 'Specialized boxes designed for biryani and rice dishes. Leak-proof with excellent heat retention and aroma preservation.',
            'subOptions': [
                {'id': 'Biryani_box2', 'name': 'Kraft Biryani Box'},
                {'id': 'biryani_box', 'name': 'Standard Biryani Box'}
            ] 
        },
        { 
            'id': 'ice cream box 2', 
            'name': 'Ice Cream Box',
            'description': 'Insulated ice cream boxes to keep frozen desserts cold. Available with slot openings for easy serving.',
            'subOptions': [
                {'id': 'ice cream box 2', 'name': 'Premium Ice Cream Box'},
                {'id': 'ice cream box', 'name': 'Standard Ice Cream Box'}
            ] 
        },
        { 
            'id': 'chocolate_box', 
            'name': 'Chocolate Box',
            'description': 'Elegant chocolate boxes for premium confectionery and gifts. Available in flat and tall handle styles with luxury finishes.',
            'subOptions': [
                {'id': 'chocolate_box', 'name': 'Flat Chocolate Box'},
                {'id': 'chocolate_box2', 'name': 'Tall Handle Chocolate Box'}
            ] 
        }
    ]
    
    try:
        data = request.json
        selected_products = data.get('products', [])
        logo_b64 = data.get('logo_b64')
        brand_name = data.get('brand_name', 'Visual Merchandising')
        color = data.get('color', '#FFFFFF')
        logo_mime_type = data.get('logo_mime_type', 'image/png')
        
        print(f"📋 VM Sheet Request:")
        print(f"   Products: {len(selected_products)}")
        print(f"   Brand: {brand_name}")
        
        if not selected_products:
            return jsonify({"error": "No products selected"}), 400
            
        if not logo_b64:
            return jsonify({"error": "Logo required"}), 400
        
        # Remove data URI prefix
        if ',' in logo_b64:
            logo_b64 = logo_b64.split(',')[1]
        
        # Expand to include sub-products
        all_products_to_generate = []
        
        for product_id in selected_products:
            product_obj = next((p for p in allProducts if p['id'] == product_id), None)
            
            if product_obj:
                if product_obj.get('subOptions') and len(product_obj['subOptions']) > 0:
                    print(f"📄 {product_id} has {len(product_obj['subOptions'])} sub-products")
                    for sub in product_obj['subOptions']:
                        all_products_to_generate.append({
                            'id': sub['id'],
                            'name': sub['name'],
                            'parent_name': product_obj['name'],
                            'description': product_obj['description']
                        })
                else:
                    all_products_to_generate.append({
                        'id': product_id,
                        'name': product_obj['name'],
                        'parent_name': product_obj['name'],
                        'description': product_obj['description']
                    })
            else:
                all_products_to_generate.append({
                    'id': product_id,
                    'name': product_id.replace('_', ' ').title(),
                    'parent_name': product_id.replace('_', ' ').title(),
                    'description': 'Premium quality packaging solution for your business needs.'
                })
        
        print(f"📦 Total products to generate: {len(all_products_to_generate)}")
        
        # Store generated mockups
        generated_images = []
        skipped_products = []
        
        # Generate mockup for each product
        for product_info in all_products_to_generate:
            product_id = product_info['id']
            print(f"\n🎨 Generating mockup for: {product_id}")
            
            product_path = PRODUCT_MAP.get(product_id)
            
            if not product_path:
                print(f"⚠️ Product not in PRODUCT_MAP: {product_id}")
                skipped_products.append(product_id)
                continue
            
            product_image_path = os.path.join(app.root_path, product_path)
            
            if not os.path.exists(product_image_path):
                print(f"⚠️ Image file not found: {product_image_path}")
                skipped_products.append(product_id)
                continue
            
            try:
                # Convert image to JPEG if needed
                with open(product_image_path, 'rb') as f:
                    product_data = f.read()
                product_b64 = base64.b64encode(product_data).decode("utf-8")
                
                if color and color.lower() != 'none':
                    color_rule = f"The primary material color of the packaging must be strictly changed to the hex color code {color}."
                else:
                    color_rule = "Keep the original packaging color or let AI choose an appropriate color based on the design."
                
                base_prompt_template = PRODUCT_PROMPTS.get(
                    product_id,
                    f"Generate a photorealistic packaging mockup. Use the first image as base product. {color_rule}"
                )
                
                base_prompt = base_prompt_template.replace('{COLOR_RULE}', color_rule)
                
                image_request_prompt = base_prompt
                if brand_name and brand_name != 'Visual Merchandising':
                    image_request_prompt += f" Use the uploaded logo prominently on the design AND also include the brand name '{brand_name}' text in a complementary elegant font near the logo."
                else:
                    image_request_prompt += " Blend the second image (logo) naturally onto the product surface with realistic lighting and perspective."
                
                parts_list = [
                    {"text": image_request_prompt},
                    {"inlineData": {"mimeType": "image/jpeg", "data": product_b64}},
                    {"inlineData": {"mimeType": logo_mime_type, "data": logo_b64}}
                ]
                
                payload = {
                    "contents": [{"parts": parts_list}],
                    "generationConfig": {"responseModalities": ["IMAGE"]}
                }
                
                headers = {"Content-Type": "application/json"}
                
                response = req.post(
                    GEMINI_IMAGE_API_URL,
                    json=payload,
                    headers=headers,
                    params={"key": API_KEY},
                    timeout=300
                )
                
                if response.status_code == 200:
                    result = response.json()
                    candidates = result.get("candidates", [])
                    
                    if candidates and "inlineData" in candidates[0].get("content", {}).get("parts", [{}])[0]:
                        img_b64 = candidates[0]["content"]["parts"][0]["inlineData"]["data"]
                        img_data = base64.b64decode(img_b64)
                        
                        generated_images.append({
                            "product_id": product_id,
                            "product_name": product_info['name'],
                            "parent_name": product_info['parent_name'],
                            "description": product_info['description'],
                            "image_data": img_data
                        })
                        print(f"✅ Mockup generated for {product_id}")
                    else:
                        print(f"⚠️ No image returned for {product_id}")
                        skipped_products.append(product_id)
                else:
                    print(f"⚠️ API error for {product_id}: {response.status_code}")
                    skipped_products.append(product_id)
                    
            except Exception as product_err:
                print(f"⚠️ Error processing {product_id}: {product_err}")
                traceback.print_exc()
                skipped_products.append(product_id)
                continue
        
        if not generated_images:
            return jsonify({"error": "No mockups could be generated"}), 500
        
        # ===== CREATE ENHANCED PDF =====
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=A4)
        width, height = A4
        
        # ===== PAGE 1: PROFESSIONAL COVER PAGE =====
        # White background
        c.setFillColor(VM_COLORS['white'])
        c.rect(0, 0, width, height, fill=True, stroke=False)
        
        # Top orange bar
        c.setFillColor(VM_COLORS['orange'])
        c.rect(0, height - 80, width, 80, fill=True, stroke=False)
        
        # Brand name in white on orange bar
        c.setFillColor(VM_COLORS['white'])
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(width/2, height - 45, brand_name if brand_name != 'Visual Merchandising' else "VISUAL MERCHANDISING")
        
        # Logo area
        try:
            logo_data = base64.b64decode(logo_b64)
            logo_img = Image.open(io.BytesIO(logo_data))
            
            # Convert to RGB if needed
            if logo_img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', logo_img.size, (255, 255, 255))
                if logo_img.mode == 'P':
                    logo_img = logo_img.convert('RGBA')
                if logo_img.mode in ('RGBA', 'LA'):
                    background.paste(logo_img, mask=logo_img.split()[-1])
                else:
                    background.paste(logo_img)
                logo_img = background
            elif logo_img.mode != 'RGB':
                logo_img = logo_img.convert('RGB')
            
            logo_buffer = io.BytesIO()
            logo_img.save(logo_buffer, format='PNG')
            logo_buffer.seek(0)
            
            logo_size = 200
            logo_x = (width - logo_size) / 2
            logo_y = height / 2 + 40
            c.drawImage(ImageReader(logo_buffer), logo_x, logo_y,
                       width=logo_size, height=logo_size,
                       preserveAspectRatio=True, mask='auto')
        except Exception as logo_err:
            print(f"⚠️ Logo error: {logo_err}")
        
        # Title
        c.setFillColor(VM_COLORS['black'])
        c.setFont("Helvetica-Bold", 48)
        c.drawCentredString(width/2, height/2 - 60, "BRANDING SHEET")
        
        # Subtitle
        c.setFont("Helvetica", 16)
        c.setFillColor(VM_COLORS['dark_gray'])
        c.drawCentredString(width/2, height/2 - 120, "Professional Product Mockups")
        
        # Footer
        c.setFont("Helvetica", 10)
        c.setFillColor(VM_COLORS['dark_gray'])
        c.drawCentredString(width/2, 60, f"Generated: {datetime.now().strftime('%d %B %Y')}")
        c.drawCentredString(width/2, 40, f"{len(generated_images)} Professional Mockups")
        c.drawCentredString(width/2, 20, "Greenwich Packaging AI • Premium Branding Solutions")
        
        c.showPage()
        
        # ===== PAGES 2+: PRODUCT MOCKUPS =====
        for idx, mockup in enumerate(generated_images):
            # White background
            c.setFillColor(VM_COLORS['white'])
            c.rect(0, 0, width, height, fill=True, stroke=False)
            
            # Top accent bar (green)
            c.setFillColor(VM_COLORS['green'])
            c.rect(0, height - 40, width, 40, fill=True, stroke=False)
            
            # Product title
            c.setFillColor(VM_COLORS['white'])
            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(width/2, height - 22, mockup['product_name'].upper())
            
            # Product description box
            c.setFillColor(VM_COLORS['light_gray'])
            c.rect(40, height - 120, width - 80, 60, fill=True, stroke=False)
            
            c.setFillColor(VM_COLORS['dark_gray'])
            c.setFont("Helvetica", 10)
            
            # Word wrap description
            desc_lines = []
            words = mockup['description'].split()
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                if c.stringWidth(test_line, "Helvetica", 10) < (width - 120):
                    current_line.append(word)
                else:
                    desc_lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                desc_lines.append(' '.join(current_line))
            
            y_pos = height - 85
            for line in desc_lines[:3]:
                c.drawCentredString(width/2, y_pos, line)
                y_pos -= 15
            
            # Product image
            try:
                img = Image.open(io.BytesIO(mockup['image_data']))
                
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if img.mode in ('RGBA', 'LA'):
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                img_width = width - 100
                img_height = height - 250
                img_x = 50
                img_y = 70
                
                c.drawImage(ImageReader(img_buffer), img_x, img_y,
                           width=img_width, height=img_height,
                           preserveAspectRatio=True, mask='auto')
            except Exception as img_err:
                print(f"⚠️ Image error: {img_err}")
            
            # Page number
            c.setFont("Helvetica", 9)
            c.setFillColor(VM_COLORS['dark_gray'])
            c.drawCentredString(width/2, 25, f"Page {idx + 2} of {len(generated_images) + 1}")
            
            c.showPage()
        
        c.save()
        pdf_buffer.seek(0)
        
        print(f"✅ Enhanced VM Sheet PDF created: 1 cover + {len(generated_images)} mockups")
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'VM_Branding_Sheet_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        print(f"❌ VM Sheet error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
