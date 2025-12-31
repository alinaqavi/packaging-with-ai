import os
import base64
import requests 
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template, url_for, redirect, send_file
from flask_cors import CORS
from google import genai 
from google.genai.errors import APIError
import fitz  # PyMuPDF
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests
import traceback
import sqlite3
import uuid

from dotenv import load_dotenv
load_dotenv()  
from flask_mail import Mail, Message
import threading
# =========================================================================
# 🚨 CONFIGURATION 🚨
# =========================================================================
API_KEY = os.environ.get("GEMINI_API_KEY") 
# Using the same image endpoint you had in your file
GEMINI_IMAGE_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent"


# Flask Setup
app = Flask(__name__)
CORS(app) 
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB for uploads
# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')  # Add to .env file
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASSWORD')  # Add to .env file
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('EMAIL_USER')

mail = Mail(app)
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
     "fries_holder": "static/fries_holder.jpeg",
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
    "paper_stand_up_bag": "static/paper_stand_up_bag.png",
    # cake,chocolate,pastry,biryani,spoon 
    "Biryani_box2": "static/biryani_box2.png",  # ✅ Fix
     "cake_box": "static/cake_box.jpeg",
     "cake_box2": "static/cake_box2.png",
     "cake_box_window": "static/cake_box_with_window.jpeg",
     "handle_cake_box": "static/handle_cake_box.jpeg",
     "chocolate_box": "static/chocolate_box.jpeg",
     "chocolate_box2": "static/chocolate_box2.jpeg",
    #"pastry_box_with_handle": "static/pastry_box_with_handle.jpeg",
     "pastry holder": "static/pastry holder.jpeg",
     "pastry holder 2": "static/pastry holder 2.jpeg",
     "k pastry holder": "static/k pastry holder.png",
     "pastry_box_with_handle": "static/pastry_box_with_handle.jpeg",
     "k pastry box": "static/k pastry box.png",
      "flat_box": "static/flat_box.png",
      "flat_box2":"static/flat_box2.png",
      "biryani_box2": "static/biryani_box2.png",
      "biryani_box":"static/biryani_box.jpeg",
      "ice cream box":"static/ice cream box.jpeg",
      "ice cream box 2":"static/ice cream box 2.png",
      "k_paper_bag_twisted": "static/k_paper_bag_twisted.png",
      "k_paper_bag_flat": "static/k_paper_bag_flat.png"
}



# -------------------------


# =========================================================================
# ✅ PRODUCT-SPECIFIC PROMPTS
# =========================================================================
PRODUCT_PROMPTS = {

    # --------------------------------------------------------------------
    # 1. PAPER BAG – Luxury Fashion Brand Style
    # --------------------------------------------------------------------
    # "paper_bag": (
    #     "Generate an ultra-luxury packaging design mockup in the style of premium fashion brands. "
    #     "Place the uploaded logo as a bold hero element on the front panel with refined balance. "
    #     "Create elegant supporting graphics inspired by the logo—minimal geometric linework, soft "
    #     "metallic accents, gradient shine, or premium monogram patterns. {COLOR_RULE} Ensure the "
    #     "design wraps naturally over folds and edges with high realism. Maintain a luxurious clean "
    #     "studio background with perfect shadows and material texture."
    # ),
  "paper_bag": (
    "Generate a packaging design that adapts fully to the brand’s identity, style, and category. Carefully analyze "
    "the uploaded logo or brand name and create visuals that represent what the brand stands for. For veggie or "
    "organic brands, use cute and friendly illustrated elements such as leaves, vegetables, soft shapes, and warm "
    "natural colors. For food brands like KFC, include chicken-related icons or bold fast-food energy. For eyewear "
    "brands, create outline silhouettes inspired by glasses. For fashion brands, keep it minimal and luxurious. "
    "Use the logo to create a repeating pattern or symbol motif across the bag, just like the reference style. "
    "Place the main branding in the center with clean, balanced typography and a warm, inviting layout. Incorporate "
    "small decorative icons that match the brand theme, arranged in a premium but playful way. {COLOR_RULE} Ensure "
    "the design wraps naturally over folds, edges, and kraft texture with soft lighting and high realism, creating a "
    "cute, premium, 3D and brand-true presentation."
),
 "k_paper_bag_flat": (
    "Generate a packaging design that adapts fully to the brand’s identity, style, and category. Carefully analyze "
    "the uploaded logo or brand name and create visuals that represent what the brand stands for. For veggie or "
    "organic brands, use cute and friendly illustrated elements such as leaves, vegetables, soft shapes, and warm "
    "natural colors. For food brands like KFC, include chicken-related icons or bold fast-food energy. For eyewear "
    "brands, create outline silhouettes inspired by glasses. For fashion brands, keep it minimal and luxurious. "
    "Use the logo to create a repeating pattern or symbol motif across the bag, just like the reference style. "
    "Place the main branding in the center with clean, balanced typography and a warm, inviting layout. Incorporate "
    "small decorative icons that match the brand theme, arranged in a premium but playful way. {COLOR_RULE} Ensure "
    "the design wraps naturally over folds, edges, and kraft texture with soft lighting and high realism, creating a "
    "cute, premium, 3D and brand-true presentation."
),
  "k_paper_bag_twisted":  (
    "Generate a packaging design that adapts fully to the brand’s identity, style, and category. Carefully analyze "
    "the uploaded logo or brand name and create visuals that represent what the brand stands for. For veggie or "
    "organic brands, use cute and friendly illustrated elements such as leaves, vegetables, soft shapes, and warm "
    "natural colors. For food brands like KFC, include chicken-related icons or bold fast-food energy. For eyewear "
    "brands, create outline silhouettes inspired by glasses. For fashion brands, keep it minimal and luxurious. "
    "Use the logo to create a repeating pattern or symbol motif across the bag, just like the reference style. "
    "Place the main branding in the center with clean, balanced typography and a warm, inviting layout. Incorporate "
    "small decorative icons that match the brand theme, arranged in a premium but playful way. {COLOR_RULE} Ensure "
    "the design wraps naturally over folds, edges, and kraft texture with soft lighting and high realism, creating a "
    "cute, premium, 3D and brand-true presentation."
),





    "flat": (
        "Generate a packaging design that adapts fully to the brand’s identity, style, and category. Carefully analyze "
    "the uploaded logo or brand name and create visuals that represent what the brand stands for. For veggie or "
    "organic brands, use cute and friendly illustrated elements such as leaves, vegetables, soft shapes, and warm "
    "natural colors. For food brands like KFC, include chicken-related icons or bold fast-food energy. For eyewear "
    "brands, create outline silhouettes inspired by glasses. For fashion brands, keep it minimal and luxurious. "
    "Use the logo to create a repeating pattern or symbol motif across the bag, just like the reference style. "
    "Place the main branding in the center with clean, balanced typography and a warm, inviting layout. Incorporate "
    "small decorative icons that match the brand theme, arranged in a premium but playful way. {COLOR_RULE} Ensure "
    "the design wraps naturally over folds, edges, and kraft texture with soft lighting and high realism, creating a "
    "cute, premium, 3D and brand-true presentation."
    ),

    "white_twisted": (
        "Generate a packaging design that adapts fully to the brand’s identity, style, and category. Carefully analyze "
    "the uploaded logo or brand name and create visuals that represent what the brand stands for. For veggie or "
    "organic brands, use cute and friendly illustrated elements such as leaves, vegetables, soft shapes, and warm "
    "natural colors. For food brands like KFC, include chicken-related icons or bold fast-food energy. For eyewear "
    "brands, create outline silhouettes inspired by glasses. For fashion brands, keep it minimal and luxurious. "
    "Use the logo to create a repeating pattern or symbol motif across the bag, just like the reference style. "
    "Place the main branding in the center with clean, balanced typography and a warm, inviting layout. Incorporate "
    "small decorative icons that match the brand theme, arranged in a premium but playful way. {COLOR_RULE} Ensure "
    "the design wraps naturally over folds, edges, and kraft texture with soft lighting and high realism, creating a "
    "cute, premium, 3D and brand-true presentation."
    ),

    "twisted": (
        "Generate a packaging design that adapts fully to the brand’s identity, style, and category. Carefully analyze "
    "the uploaded logo or brand name and create visuals that represent what the brand stands for. For veggie or "
    "organic brands, use cute and friendly illustrated elements such as leaves, vegetables, soft shapes, and warm "
    "natural colors. For food brands like KFC, include chicken-related icons or bold fast-food energy. For eyewear "
    "brands, create outline silhouettes inspired by glasses. For fashion brands, keep it minimal and luxurious. "
    "Use the logo to create a repeating pattern or symbol motif across the bag, just like the reference style. "
    "Place the main branding in the center with clean, balanced typography and a warm, inviting layout. Incorporate "
    "small decorative icons that match the brand theme, arranged in a premium but playful way. {COLOR_RULE} Ensure "
    "the design wraps naturally over folds, edges, and kraft texture with soft lighting and high realism, creating a "
    "cute, premium, 3D and brand-true presentation."
    ),

    # --------------------------------------------------------------------
    # 2. WRAPPING PAPER – Stylish Repeating Pattern
    # --------------------------------------------------------------------
 "wrapping_paper": (
    "Create a clean, minimal wrapping paper design focused entirely on the sheet itself—ignore any background or "
    "environment. Analyze the uploaded logo and transform it into a simple, elegant repeating pattern printed on kraft "
    "paper. Keep each logo moderately small with generous, even spacing around each repeat so the pattern feels modern, "
    "minimal, and breathable. Avoid heavy illustrations or busy visuals; use only light, subtle secondary motifs that "
    "match the brand theme—for example, tiny outline-style shapes related to veggies, food, bakery items, or simple "
    "geometric accents depending on the brand category. Ensure the pattern follows a neat, uniform grid layout with "
    "balanced alignment across the sheet. Do not alter the kraft base color unless the user explicitly selects another "
    "color. Render the print with crisp ink edges, soft natural shadows, gentle texture detail, and a professional "
    "studio-quality appearance that feels minimal, premium, and production-ready."
),





    # --------------------------------------------------------------------
    # 3. PAPER NAPKIN – Minimal Premium Hospitality Style
    # --------------------------------------------------------------------
    "paper_napkin": (
        'Design a premium hospitality-style napkin mockup. Place the uploaded logo centered on the '
        'top napkin in a clean, elegant layout. Add subtle embossing or pressed-texture effect to '
        'enhance luxury. {COLOR_RULE} Maintain the napkin’s natural textile texture and soft shadows '
        'for a high-end, realistic appearance.'
    ),

    # --------------------------------------------------------------------
    # 4. MEAL BOX – Modern Takeout Premium Branding
    # --------------------------------------------------------------------
    "Meal_Box": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity. Carefully "
    "analyze the brand category, theme, shapes, and colors to generate visuals that perfectly match the brand’s "
    "personality. For veggie or organic brands, use fresh, cute illustrated vegetables, leaves, and soft natural "
    "colors. For fast-food or chicken brands like KFC, use energetic, bold food icons such as chicken outlines, "
    "crispy texture graphics, or dynamic fast-food elements. For bakery brands, include warm, soft patterns like "
    "breads, buns, or sweet icons. For healthy or fitness brands, use clean modern shapes, greens, and nutrient-"
    "focused motifs. For fashion or premium brands, keep it sleek, minimal, and luxurious. Transform key shapes "
    "from the logo into a large hero graphic or pattern element across the meal box to give it a signature identity. "
    "Use the brand’s main logo prominently on the lid with balanced spacing and premium composition. Incorporate "
    "supporting icons or motifs that match the brand theme and distribute them in a high-end, clean, organized layout. "
    "{COLOR_RULE} Ensure all artwork wraps naturally over folds, edges, corners, and the kraft texture, maintaining "
    "a photorealistic, soft-shadow, premium 3D studio presentation that feels truly brand-accurate and visually rich."
),


    # --------------------------------------------------------------------
    # 5. PAPER BOWL – Smooth Curved Luxury Branding
    # --------------------------------------------------------------------
   "paper_bowl": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity. Study the logo’s "
    "shapes, curves, colors, and overall personality, then develop a delicate, refined design that visually aligns "
    "with it. For veggie or organic brands, use soft, nazuk illustrated elements like gentle leaf curves, tiny sprouts, "
    "or light botanical accents. For chicken or fast-food brands, use elegant outline-style food motifs that stay subtle "
    "and not overpowering. For bakery or dessert brands, incorporate soft pastry-inspired line art with a warm, gentle "
    "tone. For health or fitness brands, use clean, minimal modern micro-graphics. For luxury or premium brands, keep "
    "the design extremely minimal, balanced, and elegant with fine-line detailing. Transform one key shape from the "
    "logo into a delicate signature motif that wraps gracefully around the bowl’s curved surface, ensuring it complements "
    "the brand’s visual language. Place the main logo prominently but with soft, breathable spacing to maintain a high-end "
    "look. Add only a few nazuk supporting icons that follow the natural circular flow of the bowl, keeping the overall "
    "layout light, premium, and beautifully composed. {COLOR_RULE} Ensure the artwork wraps smoothly along the bowl’s "
    "geometry with realistic curvature, crisp ink lines, subtle kraft texture, natural print absorption, soft shadows, "
    "and a polished studio-quality finish that feels elegant, clean, and perfectly matched to the brand."
),




    "with_lid": (
        "Create a premium bowl-with-lid mockup. Apply the logo elegantly on the bowl body. Add "
        "luxury minimal accents around the body inspired by the logo’s shapes. {COLOR_RULE} Maintain "
        "curvature realism, natural shadows, and premium paper texture."
    ),

    "without_lid": (
        "Generate a high-end bowl mockup without a lid. Integrate the logo as a clean hero element on "
        "the curved exterior surface. Add abstract decorative shapes or modern patterns inspired from "
        "the logo. {COLOR_RULE} Maintain smooth curvature alignment and high-quality shadows."
    ),

    # --------------------------------------------------------------------
    # 6. CUPS – Luxury Coffeehouse Aesthetic
    # --------------------------------------------------------------------
    "paper_cup": (
        "Design a premium beverage cup mockup inspired by luxury coffeehouse branding (Starbucks Reserve, "
        "Blue Bottle Special Edition, %Arabica premium line). Apply the uploaded logo at the center. Add "
        "elegant modern design accents—smooth gradient rings, soft flowing lines, minimal geometry, or "
        "high-end pattern overlays. {COLOR_RULE} Ensure perfect cylindrical wrapping, highlights, and "
        "cup material texture."
    ),

    "single_wall": (
        "Generate a modern, premium single-wall cup mockup. Use the logo prominently, with supporting "
        "decor inspired by luxury coffee brand geometry. {COLOR_RULE} Maintain photorealistic curvature "
        "and shadow depth."
    ),

    "double_wall": (
        "Create a luxury double-wall beverage cup mockup. Place the uploaded logo cleanly and symmetrically. "
        "Add elegant patterns or abstract shapes inspired from the logo. {COLOR_RULE} Ensure realistic "
        "double-wall depth, rim lighting, and clean shadows."
    ),

    # --------------------------------------------------------------------
    # 7. PIZZA BOXES – Premium Food Packaging
    # --------------------------------------------------------------------
    "pizza_box": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity. Carefully "
    "analyze the brand category, style, shapes, and color language to develop visuals that perfectly reflect the "
    "brand’s personality. For pizza, fast-food, or Italian-inspired brands, use clean illustrated elements such as "
    "pizza slices, cheese drips, herbs, tomato shapes, or subtle Italian patterns. For chicken-based or spicy brands, "
    "include bold outline-style food icons with energetic fast-food accents. For veggie or organic brands, integrate "
    "soft illustrated vegetables, leafy motifs, or natural shapes in a cute, fresh style. For bakery or dessert-oriented "
    "brands, add warm and friendly pastry-like symbols. For premium or fashion-driven brands, keep the design extremely "
    "minimal, using elegant composition and refined negative space. Transform key shapes from the logo into a large hero "
    "graphic or a custom pattern that sits proudly on the pizza box lid, giving the packaging a signature identity. Place "
    "the main logo prominently on the top with balanced spacing and strong visual hierarchy. Add light supporting motifs "
    "on the side panels in a clean, organized rhythm to enhance the branding without clutter. {COLOR_RULE} Ensure all "
    "artwork wraps naturally across the flat lid, edges, folds, and kraft texture with crisp ink detailing, soft realistic "
    "shadows, and a high-end studio appearance that feels premium, brand-accurate, and visually engaging."
),


    "white_pizza_box": (
       "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity. Carefully "
    "analyze the brand category, style, shapes, and color language to develop visuals that perfectly reflect the "
    "brand’s personality. For pizza, fast-food, or Italian-inspired brands, use clean illustrated elements such as "
    "pizza slices, cheese drips, herbs, tomato shapes, or subtle Italian patterns. For chicken-based or spicy brands, "
    "include bold outline-style food icons with energetic fast-food accents. For veggie or organic brands, integrate "
    "soft illustrated vegetables, leafy motifs, or natural shapes in a cute, fresh style. For bakery or dessert-oriented "
    "brands, add warm and friendly pastry-like symbols. For premium or fashion-driven brands, keep the design extremely "
    "minimal, using elegant composition and refined negative space. Transform key shapes from the logo into a large hero "
    "graphic or a custom pattern that sits proudly on the pizza box lid, giving the packaging a signature identity. Place "
    "the main logo prominently on the top with balanced spacing and strong visual hierarchy. Add light supporting motifs "
    "on the side panels in a clean, organized rhythm to enhance the branding without clutter. {COLOR_RULE} Ensure all "
    "artwork wraps naturally across the flat lid, edges, folds, and kraft texture with crisp ink detailing, soft realistic "
    "shadows, and a high-end studio appearance that feels premium, brand-accurate, and visually engaging."
),

    "triangular_pizza_box": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity. Carefully "
    "analyze the brand category, theme, shapes, and colors to craft visuals that perfectly match the brand's "
    "personality. For pizza, fast-food, or Italian-style brands, incorporate clean illustrated pizza slice motifs, "
    "cheese drips, herbs, or tomato accents designed to complement the triangular shape of the box. For chicken or "
    "spicy brands, use bold yet minimal outline-style food icons. For veggie or organic brands, include fresh and "
    "soft illustrated vegetables or leafy motifs. For bakery or dessert brands, integrate warm pastry-inspired icons. "
    "For luxury or premium brands, keep the design extremely minimal and refined. Transform a key shape from the logo "
    "into a hero graphic placed prominently in the upper center of the triangular lid, allowing the geometry to guide "
    "the flow of the design. Add supporting motifs along the angled edges to enhance the visual rhythm while keeping "
    "the layout clean and balanced. {COLOR_RULE} Ensure the artwork wraps realistically across the triangular lid, "
    "folds, and side walls with crisp ink detailing, subtle texture, soft shadows, and a polished studio-grade finish "
    "that feels premium, brand-authentic, and visually engaging."
),


    # --------------------------------------------------------------------
    # 8. BURGER BOX – Elegant Food Packaging
    # --------------------------------------------------------------------
  "burger_box": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity. Carefully "
    "study the brand’s category, theme, shapes, and colors to craft visuals that perfectly express its personality. "
    "For fast-food, burger, or chicken brands, use clean illustrated elements such as burger outlines, grill marks, "
    "flame shapes, or minimal food icons. For veggie or organic brands, integrate soft leaf motifs, sprouts, or "
    "fresh illustrated vegetables. For bakery or dessert brands, use warm pastry-inspired details. For healthy or "
    "fitness brands, incorporate clean geometric accents with fresh, modern tones. For premium or fashion-driven "
    "brands, keep the design extremely minimal, elegant, and well-spaced. Transform key shapes from the logo into a "
    "signature hero graphic placed prominently on the top lid, giving the burger box a distinctive visual identity. "
    "Add subtle supporting motifs along the top edges and side panels in a clean, organized rhythm, ensuring the "
    "layout never looks cluttered. Place a small upright logo or brand symbol on the front flap in a straight, "
    "centered orientation for refined branding. {COLOR_RULE} Ensure all artwork wraps naturally across the folds, "
    "curves, lid edges, and kraft-paper texture with crisp ink lines, soft shadows, realistic print absorption, and "
    "a polished studio-grade finish that feels premium, brand-authentic, and visually balanced."
),


    # --------------------------------------------------------------------
    # 9. SANDWICH BOXES – Modern Minimal Luxury
    # --------------------------------------------------------------------
     "sandwich_box": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity, specifically for "
    "a triangular wedge-style sandwich box that includes a clear front window. Carefully analyze the brand category, "
    "theme, shapes, and color language to generate visuals that perfectly match the brand’s personality. For veggie or "
    "organic brands, use fresh, cute illustrated leaves, herbs, sprouts, or soft natural vegetable accents placed only on "
    "the printable kraft areas. For fast-food or chicken brands, incorporate energetic, bold outline-style food icons or "
    "dynamic fast-food elements. For bakery or café brands, include warm, soft pastry or bread-inspired motifs. For "
    "healthy or fitness brands, use clean modern shapes, greens, and nutrient-focused micro-icons. For premium or fashion "
    "brands, keep the composition sleek, minimal, and luxurious. Transform key shapes from the logo into a large hero "
    "graphic placed prominently on the top slanted lid to give the packaging a strong signature identity. Do NOT place "
    "any artwork on the clear window or inside the window framing area. Use supporting icons or motifs only on the top "
    "surface and angled side panels in a clean, organized layout that follows the triangular geometry of the box. "
    "{COLOR_RULE} Ensure all artwork wraps naturally over folds, angled planes, panel intersections, and the kraft "
    "texture, maintaining realistic ink behavior, soft shadows, and a premium 3D studio presentation that feels truly "
    "brand-accurate, polished, and visually rich."
),

   "sandwich_box2": "Generate a full, highly realistic takeout packaging studio mockup. Integrate the uploaded logo as a large, primary graphic centered on the top lid of the sandwich box. Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns onto the side panels of the box, inspired by the style of the logo or the product's function, to create a complete, branded look. {COLOR_RULE} The design must be realistically applied with texture, lighting, and shadows. The background environment of the mockup should remain unchanged.",




    # --------------------------------------------------------------------
    # 10. ROLL BOXES – Premium Modern Cylinder/Slide Packaging
    # --------------------------------------------------------------------
    "roll_box": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity, specifically for "
    "a long curved pillow-style roll box with rounded edges and side tuck flaps. The background must remain a clean, "
    "neutral premium studio backdrop—do NOT modify or recolor the background. Only the box surface is allowed to receive "
    "designs, motifs, or {COLOR_RULE} adjustments. Carefully analyze the brand’s category, theme, shapes, and visual "
    "language to generate artwork that fits both the brand personality and the smooth curved surface of this packaging. "
    "Place the main logo prominently at the center without distortion, and add subtle supporting motifs that follow the "
    "curved flow of the box. Keep all elements minimal, refined, and clean unless the brand identity is bold and energetic. "
    "Ensure all artwork wraps naturally across the curved front, rounded edges, and side flaps with crisp ink detailing, "
    "realistic paper texture, and a polished high-end studio-quality finish while keeping the background untouched and "
    "perfectly neutral."
),


    "roll_locking_box": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity, specifically for "
    "a long rectangular roll-locking box with a front locking flap and clean flat surfaces. The background must remain "
    "a neutral premium studio backdrop—do NOT modify or recolor the background. Only apply design elements and {COLOR_RULE} "
    "to the box surface. Analyze the brand category, theme, shapes, and color language to generate visuals that perfectly "
    "match the brand’s personality. For veggie or organic brands, use fresh illustrated leaves, herbs, or soft natural "
    "vegetable accents placed in a minimal and refined way. For fast-food or chicken brands, incorporate energetic, bold "
    "outline-style food icons or dynamic accents. For bakery or café brands, include warm, soft pastry-inspired motifs. "
    "For healthy or fitness brands, use clean modern shapes, greens, and nutrient-focused micro-icons. For premium fashion-"
    "style brands, keep the composition sleek, minimal, and luxurious with elegant negative space. Transform key shapes "
    "from the logo into a large hero graphic placed prominently on the top panel, giving the packaging a signature identity. "
    "Place the main logo on the lid with balanced spacing, and add supporting motifs on the long side panels in a clean, "
    "organized rhythm that follows the linear geometry of the box. Avoid placing artwork on the locking mechanism edges to "
    "maintain clarity. Ensure all artwork wraps naturally over the flat lid, long side walls, folded corners, and locking "
    "flap with crisp ink detailing, realistic paper texture, and a premium studio-quality 3D finish that feels polished, "
    "brand-accurate, and visually rich."
),

   "roll_sliding_box": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity, specifically for "
    "a two-part roll-style sliding box consisting of an outer sleeve and a white inner tray. The inner tray must remain "
    "completely plain white at all times — do NOT apply any artwork, colors, patterns, or logos to the tray under any "
    "circumstances. Only the outer sleeve should contain all design elements, motifs, and {COLOR_RULE} adjustments. The "
    "background must remain a clean, neutral studio backdrop — do NOT modify or recolor the background. Analyze the brand "
    "category, theme, shapes, and color language to generate visuals that perfectly match the brand’s personality. Place "
    "the main logo prominently on the flat top surface of the sleeve with balanced spacing. Add subtle supporting motifs "
    "along the long side panels following the linear geometry of the box. Ensure all artwork wraps naturally over the "
    "sleeve’s folds, edges, and sliding seams while keeping the inner tray untouched, clean, and bright white. Maintain "
    "crisp ink detailing, soft shadows, accurate paper texture, and a premium photorealistic studio finish."
),




    # --------------------------------------------------------------------
    # 11. NOODLE / PASTA BOX – Premium Asian Fusion Aesthetic
    # --------------------------------------------------------------------
    "noodle_pasta_box": (
        "Generate a high-end noodle/pasta box mockup with the uploaded logo as the main graphic. Add elegant "
        "supporting accents—soft line waves, minimal geometric strokes, or modern cultural patterns inspired "
        "by the logo. {COLOR_RULE} Maintain box curvature, folds, and lighting realism."
    ),

    # --------------------------------------------------------------------
    # 12. POPCORN HOLDER – Modern Cinema Luxury Style
    # --------------------------------------------------------------------
"popcorn_holder": (
    "Design a highly polished, premium popcorn/snack holder layout that adapts beautifully to the uploaded logo and "
    "brand theme. Ensure all four tapered walls of the box receive a clean, well-balanced design. The background pattern "
    "should vary creatively based on brand identity—this may include vertical stripes, soft curved bands, retro cinema "
    "motifs, dotted patterns, popcorn clouds, geometric shapes, or cute illustrated elements. The pattern must always "
    "follow the taper of the box, becoming slightly narrower toward the base to maintain realism. Place the brand logo "
    "on each of the four walls in centered, proportionate alignment with smooth spacing around it so it always appears "
    "crisp and premium. Include small supportive icons (like fries, drinks, popcorn kernels, or brand-relevant food/"
    "theme symbols) positioned tastefully between pattern elements without clutter. The design should feel lively but "
    "clean, playful yet professional. {COLOR_RULE} Keep the interior of the box pure white with all artwork applied only "
    "to the exterior. Ensure the final output has realistic print texture, natural shadows, clean ink edges, and a high-"
    "quality studio appearance. The design should look commercially viable, visually appealing, and perfectly wrapped "
    "across all four angled panels."
),

"fries_holder":(
    "Design a highly polished, premium popcorn/snack holder layout that adapts beautifully to the uploaded logo and "
    "brand theme. Ensure all four tapered walls of the box receive a clean, well-balanced design. The background pattern "
    "should vary creatively based on brand identity—this may include vertical stripes, soft curved bands, retro cinema "
    "motifs, dotted patterns, popcorn clouds, geometric shapes, or cute illustrated elements. The pattern must always "
    "follow the taper of the box, becoming slightly narrower toward the base to maintain realism. Place the brand logo "
    "on each of the four walls in centered, proportionate alignment with smooth spacing around it so it always appears "
    "crisp and premium. Include small supportive icons (like fries, drinks, popcorn kernels, or brand-relevant food/"
    "theme symbols) positioned tastefully between pattern elements without clutter. The design should feel lively but "
    "clean, playful yet professional. {COLOR_RULE} Keep the interior of the box pure white with all artwork applied only "
    "to the exterior. Ensure the final output has realistic print texture, natural shadows, clean ink edges, and a high-"
    "quality studio appearance. The design should look commercially viable, visually appealing, and perfectly wrapped "
    "across all four angled panels."
),


   "popcorn_holder": (
    "Design a highly polished, premium popcorn/snack holder layout that adapts beautifully to the uploaded logo and "
    "brand theme. Ensure all four tapered walls of the box receive a clean, well-balanced design. The background pattern "
    "should vary creatively based on brand identity—this may include vertical stripes, soft curved bands, retro cinema "
    "motifs, dotted patterns, popcorn clouds, geometric shapes, or cute illustrated elements. The pattern must always "
    "follow the taper of the box, becoming slightly narrower toward the base to maintain realism. Place the brand logo "
    "on each of the four walls in centered, proportionate alignment with smooth spacing around it so it always appears "
    "crisp and premium. Include small supportive icons (like fries, drinks, popcorn kernels, or brand-relevant food/"
    "theme symbols) positioned tastefully between pattern elements without clutter. The design should feel lively but "
    "clean, playful yet professional. {COLOR_RULE} Keep the interior of the box pure white with all artwork applied only "
    "to the exterior. Ensure the final output has realistic print texture, natural shadows, clean ink edges, and a high-"
    "quality studio appearance. The design should look commercially viable, visually appealing, and perfectly wrapped "
    "across all four angled panels."
),


    # --------------------------------------------------------------------
    # 13. PAPER TRAY – Minimal Modern Food Tray
    # --------------------------------------------------------------------
    "paper_tray": (
        "Produce a high-end paper food tray mockup. Apply the uploaded logo elegantly on one side panel. "
        "Add subtle premium patterning or decorative accents inspired from the logo. {COLOR_RULE} Maintain "
        "realistic shadows, folds, and paper texture."
    ),

    # --------------------------------------------------------------------
    # 14. STAND-UP BAGS – Premium Doypack / Pouch Branding
    # --------------------------------------------------------------------
    "white_paper_stand_up_bag": (
    "Create a fully brand-adaptive packaging design tailored carefully to the uploaded logo and brand identity. "
    "Study the product shape: a stand-up food bag with a die-cut handle on top and a large transparent front window. "
    "Apply all artwork only on the exterior paper surfaces and keep the inside completely white. Never cover or distort "
    "the transparent window—leave that area clean and visible. Use the upper front area above the window and all side "
    "panels for branding. Place the main logo in a balanced, premium position above the window with perfect alignment. "
    "Design supporting graphics that reflect the brand category: cute vegetables for veggie brands, energetic fast-food "
    "icons for burger or chicken brands, bakery-inspired motifs for dessert brands, or minimal luxurious shapes for "
    "premium fashion-like branding. Include subtle patterns or symbols on the side panels, maintaining clean spacing and "
    "a soft, modern visual flow. You may create repeating motifs, gentle stripes, small illustrated accents, or elegant "
    "geometric backgrounds based on the brand style—ensure the graphics stop cleanly around the window frame. Use refined "
    "composition and smooth visual hierarchy so the design never feels crowded. {COLOR_RULE} Ensure realistic paper texture, "
    "natural shadows, crisp ink edges, and a high-end studio-quality appearance. Keep the final mockup photorealistic, "
    "professionally printed, and true to the shape of the stand-up window food bag."
),


    "paper_stand_up_bag": (
        "Create a modern kraft stand-up pouch mockup. Place the uploaded logo elegantly. Add supporting "
        "premium brand elements derived from logo geometry or flow. {COLOR_RULE} Maintain kraft texture realism, "
        "folds, and clean lighting."
    ),

    "cake_box": (
    "Create a fully brand-adaptive premium cake box design tailored to the uploaded logo and brand theme. Analyze the "
    "logo style and the product category to generate visuals that match perfectly—cute bakery icons for dessert brands, "
    "luxury minimalist accents for premium bakeries, or playful illustrated sweets for fun brands. Place the main logo "
    "centrally on the top lid with balanced spacing and clean hierarchy. Enhance the side panels with subtle patterns, "
    "soft graphic lines, doodle-style bakery elements, or elegant repeating motifs inspired by the logo. Maintain a clean, "
    "organized layout that feels premium and commercially printed. {COLOR_RULE} Apply the design realistically across the "
    "flat lid, curved edges, and side flaps, ensuring accurate shadows, paper texture, and crisp print quality. Keep the "
    "background studio environment unchanged and professionally lit."
),

"cake_box_window": (
    "Create a premium, brand-adaptive cake box design specifically for a box with a transparent top window. Keep the "
    "window area completely clean and uncovered. Place the uploaded logo elegantly above or around the window frame with "
    "perfect alignment. Use the remaining lid surface to apply soft patterns, bakery-themed illustrations, or minimal "
    "accent graphics inspired by the logo’s style without touching the window. Decorate the side panels with complementary "
    "motifs such as cupcakes, pastries, swirls, stripes, or refined geometric shapes, depending on the brand identity. "
    "{COLOR_RULE} Maintain clean, realistic print application across folds, edges, and the paper texture, with accurate "
    "lighting and shadows. The mockup background must remain unchanged and studio-quality."
),

  "handle_cake_box": (
    "Create a fully brand-adaptive premium design for a cake box with an integrated carry handle. Analyze the uploaded "
    "logo and use it as the main hero graphic placed prominently on the top surface or just below the handle area with "
    "clean spacing. Incorporate supporting bakery-inspired illustrations, elegant patterns, or cute sweet-themed icons "
    "across the front and side panels while keeping the handle structure clean and readable. Ensure the artwork follows "
    "the box’s unique shape, wrapping naturally around its vertical walls and curved handle cuts. {COLOR_RULE} Maintain a "
    "highly realistic printed look with proper shadows, depth, paper texture, and accurate edge wrapping. Keep the studio "
    "background unchanged and professional."
),

    "chocolate_box": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity. Carefully "
    "analyze the brand category, theme, shapes, and colors to generate visuals that perfectly match the brand’s "
    "personality. Since this is a premium flat chocolate box, focus on elegant, minimal, luxurious styling. Use "
    "refined shapes, thin line motifs, chocolate-inspired icons, or soft patterns that enhance the high-end feel. "
    "Transform key shapes from the logo into a clean hero graphic placed prominently on the top lid with perfect "
    "spacing and balance. Add subtle supporting elements or patterns around the side walls to create a premium "
    "complete look without clutter. {COLOR_RULE} The inside area must remain plain white exactly like the physical "
    "product. Ensure all artwork wraps realistically across the lid edges, folds, and box contours with premium "
    "studio lighting, soft shadows, and true-to-life texture application, keeping the background environment unchanged."
),

 "chocolate_box2": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity. Carefully "
    "analyze the brand category, theme, shapes, and colors to produce visuals that perfectly match the brand’s "
    "personality. Because this is a tall, premium handle-style chocolate box, use vertical layout-aware graphics, "
    "elegant motifs, soft luxury patterns, or minimal iconography that suits a gift-style product. Place the main "
    "logo prominently on the front panel at balanced height, maintaining strong visual hierarchy. Integrate subtle "
    "supporting elements on the sides to enhance identity while keeping the design classy and clean. {COLOR_RULE} "
    "The inside of the box must remain fully white as in the real structure. Ensure all artwork wraps naturally over "
    "the curved edges, handle cutout, folds, and vertical planes with crisp texture, soft shadows, and lifelike "
    "3D studio realism. Background environment must remain unchanged."
),
   
     "pastry_box_with_handle": (
    "Generate a highly realistic studio mockup of the upright pastry gable box with a built-in handle. "
    "Carefully apply the uploaded logo as the main hero graphic on the wide front panel, aligned to the flat surface "
    "without warping. Add light, elegant supporting branding elements such as thin lines, soft curves, or minimal "
    "pattern accents inspired by the logo style. Keep side panels branded but clean, with subtle motifs only. "
    "{COLOR_RULE} Ensure print sits accurately on the kraft/paper texture, respecting folds, curves, locking tabs, "
    "and the angled roof panels leading to the handle. Maintain realistic shadows, highlights, and original background."
),

 "pastry holder": (
    "Generate a photorealistic studio mockup of the triangular open-top pastry holder tray. "
    "Place the uploaded logo prominently on the front rim panel, scaled realistically for the shallow structure. "
    "Use very minimal decorative elements—thin strokes, tiny icons, or a simple repeating border along the rim—"
    "to keep the tray premium and clean. Avoid heavy graphics inside; interior must stay plain white. "
    "{COLOR_RULE} Artwork must wrap naturally around the curved edges and shallow triangular walls with accurate lighting."
),

   "pastry holder 2": (
    "Create a realistic mockup for the white triangular pastry tray with open top. "
    "Integrate the logo as a neat, centered mark on the front outer panel, keeping the look minimal and elegant. "
    "Apply soft supporting motifs or a gentle geometric pattern only on the outside walls. "
    "Interior must remain completely white and untouched. {COLOR_RULE} Respect the paper texture, folds, and rounded corners "
    "with natural shadows and correct perspective."
),

"k pastry holder": (
    "Generate a highly realistic mockup of the tall curved pastry holder with a standing vertical form. "
    "Place the uploaded logo on the wider front panel, keeping alignment with the curved contour. "
    "Use minimal, vertical-flow supporting graphics that match the tall shape—such as soft stripes, gradients, "
    "or simple repeating icons. Avoid clutter. {COLOR_RULE} Ensure perfect wrapping around the curved surface, "
    "realistic lighting, and crisp paper texture."
),

 "k pastry box": (
    "Generate a premium studio mockup of the small square pastry box with a simple folding lid. "
    "Center the uploaded logo on the lid as the primary branding element. "
    "Use subtle supporting design—tiny icons, soft lines, or a faint repeating pattern—on the side panels only. "
    "{COLOR_RULE} Ensure artwork follows the box folds accurately and maintains photorealistic lighting, texture, and shadows."
),


    "flat_box": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity. Carefully "
    "analyze the brand category, theme, shapes, and colors to generate visuals that perfectly match the brand’s "
    "personality. Since this is a flat rectangular food box, use a clean hero graphic on the top lid inspired by "
    "the uploaded logo, keeping the composition balanced and minimal. Add subtle supporting motifs or patterns on "
    "the side panels that follow the brand theme, such as thin lines, tiny icons, or soft patterns that enhance the "
    "overall design without overcrowding the box. Transform key shapes from the logo into elegant accents across "
    "the flat lid and side walls to give the box a cohesive identity. Place the main logo prominently on the center "
    "of the lid with visually pleasing spacing and hierarchy. {COLOR_RULE} Ensure all artwork wraps naturally over "
    "the edges, curved front flap, folds, and the box’s material texture while maintaining photorealistic lighting, "
    "soft shadows, and a premium studio look that feels truly brand-accurate and visually rich."
),
"flat_box2": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity. Carefully "
    "analyze the brand category, theme, shapes, and colors to generate visuals that perfectly match the brand’s "
    "personality. For this kraft flat food box, use a strong hero logo placement on the top lid to ensure high "
    "visibility on natural kraft texture. Add subtle, brand-inspired supporting graphics on the side walls such as "
    "minimal line accents, food-related icons, or pattern elements that complement the kraft tone. Transform logo "
    "shapes or signature curves into clean decorative elements across the box for a cohesive premium identity. "
    "Place the main logo centered on the lid with balanced spacing. {COLOR_RULE} Ensure all artwork wraps cleanly "
    "over the edges, folds, and curved front flap with realistic ink behavior on kraft material, soft shadows, and "
    "professional studio lighting for a visually rich, photorealistic appearance."
),
  
    "biryani_box": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity. Carefully "
    "analyze the brand category, theme, shapes, and colors to generate visuals that perfectly match the brand’s "
    "personality. As this is a biryani-style food box, incorporate subtle food-related motifs such as spices, herbs, "
    "or steam lines that enhance the brand identity in a clean way. Transform shapes from the logo into a hero "
    "graphic on the lid and lightly distribute supporting motifs across the side panels, keeping the overall visual "
    "organized and modern. Place the main logo prominently on the top lid with balanced spacing and strong visual "
    "hierarchy. {COLOR_RULE} Ensure all artwork wraps naturally over folds, curved flaps, edges, and material texture "
    "while maintaining photorealistic shadows, clean lighting, and a premium 3D studio presentation that feels "
    "truly brand-accurate and visually rich."
),
"biryani_box2": (
    "Create a fully brand-adaptive packaging design tailored to the uploaded logo and brand identity. Carefully "
    "analyze the brand category, theme, shapes, and colors to generate visuals that perfectly match the brand’s "
    "personality. For this kraft biryani box, apply a bold hero logo on the top lid that contrasts well with the "
    "kraft texture. Add minimal spice-inspired elements, clean line accents, or small food icons on the side panels "
    "to elevate the brand’s theme without overwhelming the natural material. Transform key logo shapes into soft "
    "decorative elements across the lid and edges for a cohesive design. Place the main logo prominently on the top "
    "lid with clear, premium spacing. {COLOR_RULE} Ensure all artwork wraps realistically across kraft folds, curved "
    "flaps, and edges with accurate shadows, lighting, and texture, creating a premium studio-quality presentation."
),

     "ice_cream_box2":(
"Generate a full, highly realistic takeout packaging studio mockup. Integrate the uploaded logo as a large, primary graphic centered on the top lid of the long rectangular box. Generate and apply complementary branding elements, clean graphic lines, or subtle repeating patterns across the long side walls of the box, inspired by the logo style and the product’s dessert theme, to create a complete and cohesive branded look. {COLOR_RULE} Keep the inside of the box plain and unprinted. Ensure the artwork wraps naturally over edges, corners, and long panels with photorealistic texture, lighting, and shadows. The background environment of the mockup must remain unchanged."
     ),

    "ice_cream_box":(
"Generate a full, highly realistic takeout packaging studio mockup. Integrate the uploaded logo as a large, primary graphic centered on the top face of the box without interfering with the slot opening. Apply complementary branding elements, minimal dessert-themed patterns, or clean graphic accents on the side panels to create a cohesive branded look. {COLOR_RULE} Keep the interior plain white. Ensure the artwork is applied realistically over the curved lid and edges with accurate shadows and material texture. The background environment must remain unchanged."
    ),
     
}


# =========================================================================
# HELPER FUNCTIONS
# =========================================================================



def convert_pdf_to_png(pdf_b64):
    """✅ Convert PDF to PNG using PyMuPDF (No Poppler required)."""
    try:
        print("📄 Converting PDF to PNG using PyMuPDF...")
        pdf_bytes = base64.b64decode(pdf_b64)
        
        # Open PDF from memory
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if doc.page_count < 1:
            raise ValueError("PDF has no pages")

        # Get the first page
        page = doc.load_page(0)
        
        # Render to image (zoom=2 for higher resolution, approx 144 DPI)
        # Increase zoom to 4 for 300 DPI equivalent
        matrix = fitz.Matrix(2, 2) 
        pix = page.get_pixmap(matrix=matrix, alpha=True) # alpha=True keeps transparency
        
        # Convert to PNG bytes
        png_bytes = pix.tobytes("png")
        
        # Encode back to base64 string
        png_b64 = base64.b64encode(png_bytes).decode("utf-8")
        
        doc.close()
        print(f"✅ PDF converted successfully (size: {len(png_b64)} chars)")
        return png_b64
        
    except Exception as e:
        print(f"❌ PDF conversion error: {e}")
        traceback.print_exc()
        raise

def convert_to_jpeg_if_unsupported(image_path):
    """Convert unsupported formats to JPEG and return (bytes, mime)."""
    file_extension = image_path.split('.')[-1].lower()
    
    # âœ… Directly supported formats - no conversion needed
    if file_extension in ['jpeg', 'jpg', 'png']:
        with open(image_path, "rb") as f:
            data = f.read()
        return data, f"image/{'jpeg' if file_extension in ['jpg', 'jpeg'] else 'png'}"
    
    # âœ… Convert these formats to PNG (better quality than JPEG for logos)
    if file_extension in ['webp', 'avif', 'gif', 'bmp', 'tiff', 'tif', 'svg']:
        print(f"âš  Converting {file_extension} to PNG")
        img = Image.open(image_path)
        
        # Handle animated GIFs - take first frame
        if file_extension == 'gif' and getattr(img, 'is_animated', False):
            print("ðŸŽžï¸ Animated GIF detected - using first frame")
            img.seek(0)
        
        # Convert to RGB if necessary (for formats with transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue(), "image/png"
    
    raise ValueError(f"Unsupported format: {file_extension}")



def convert_logo_format(logo_b64, mime_type):
    """
    âœ… Convert any logo format to PNG for consistency.
    Handles: PDF, GIF, WEBP, AVIF, BMP, TIFF, SVG, etc.
    Returns: (converted_base64, new_mime_type)
    """
    try:
        # If already PNG or JPEG, no conversion needed
        if mime_type in ['image/png', 'image/jpeg', 'image/jpg']:
            return logo_b64, mime_type
        
        # Informational log about conversion
        print(f"Converting {mime_type} to PNG...")
        
        # Decode base64
        file_data = base64.b64decode(logo_b64)
        
        # Special handling for PDF
        if mime_type == 'application/pdf':
            return convert_pdf_to_png(logo_b64), 'image/png'
        
        # Handle image formats
        img = Image.open(BytesIO(file_data))
        
        # Handle animated GIFs - use first frame
        if mime_type == 'image/gif' and getattr(img, 'is_animated', False):
            print("ðŸŽžï¸ Animated GIF detected - extracting first frame")
            img.seek(0)
        
        # Convert to RGB if necessary (preserve transparency by adding white background)
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
        
        # Save as PNG
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        png_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        
        print(f"âœ… Converted to PNG successfully (size: {len(png_b64)} chars)")
        return png_b64, 'image/png'
        
    except Exception as e:
        print(f"âŒ Logo conversion error: {e}")
        traceback.print_exc()
        raise




def validate_international_phone(phone):
    # The frontend sends E.164 format (e.g., +14155552671)
    # We just need to check if it's not empty and has a reasonable length
    if not phone or len(phone) < 5:
        return False
    return True


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


# # =========================================================================
# # ✅ SMART CHATBOT: DESIGN CHAT + IMAGE EDIT + PRODUCT SELECTION (FINAL)
# # =========================================================================
# @app.route('/send_chat', methods=['POST'])
# def send_chat():
#     """Smart chatbot that understands edit requests, product changes, and design chat."""
#     global PRODUCT_MAP # Ensure PRODUCT_MAP is accessible

#     if not chat_client:
#         return jsonify({"error": "AI services unavailable.", "message": "AI chatbot is currently offline. Please try again later."}), 200

#     try:
#         data = request.json or {}
#         chat_history = data.get('history', [])
#         # Product name is the name currently selected in the UI
#         product_name = data.get('product_name', 'packaging item')
#         color = data.get('color', 'default color')
#         image_b64 = data.get('image_b64') 
#         image_mime = data.get('image_mime', 'image/png')

#         user_message = ""
#         if chat_history:
#             for msg in reversed(chat_history):
#                 if msg.get('role') == 'user':
#                     user_message = msg.get('content', '')
#                     break

#         print(f"📨 Chat request received | Current Product: {product_name} | Color: {color}")
#         print(f"💬 User message: {user_message[:200]}")

#         # ---------------------------------------------------------------------
#         # 🧹 FIX: Product Change Detection and Chat Reset
#         # ---------------------------------------------------------------------
#         last_product = None
#         # Find the last product mentioned in the chat history for comparison
#         for msg in reversed(chat_history):
#             if "Product:" in msg.get("content", ""):
#                 last_product = msg["content"].split("Product:")[-1].strip()
#                 break

#         product_changed = False
#         if last_product and last_product.lower() != product_name.lower():
#             product_changed = True
#             print(f"🧹 Product changed from {last_product} → {product_name}. Full chat reset triggered.")
#             # Important: Reset chat history so the AI's context is updated for the new product
#             chat_history = []
#             system_reset_message = f"Product changed: Now focusing only on {product_name}. Ignore all previous design prompts or instructions."
#             user_message = system_reset_message


#         # --- Intent Detection ---
#         message_lower = user_message.lower()
#         intent = "design_chat"
        
#         # Keywords for intent classification
#         image_edit_keywords = ["shine", "gloss", "color", "matte", "texture", "background", "font", "make it", "change color", "edit", "modify"]
#         product_selection_keywords = ["select the product for me", "choose product", "suggest a product", "kon sa product", "product batao", "product select karo", "product recommend", "konsa product", "kaun sa product"]
        
#         # Check if the user's current message is a conversational product selection itself.
#         is_product_selection_query = any(k in message_lower for k in product_selection_keywords) or ("product" in message_lower and "select" in message_lower)

#         # 🎯 PRIORITY 1: UI Product Change Acknowledgment (New Logic)
#         if product_changed and not is_product_selection_query:
#             intent = "product_change_notification"
        
#         # 🎯 PRIORITY 2: IMAGE EDIT 
#         elif any(k in message_lower for k in image_edit_keywords) and image_b64:
#             intent = "image_edit"
        
#         # 🎯 PRIORITY 3: CONVERSATIONAL PRODUCT SELECTION (User typed the selection request)
#         elif is_product_selection_query:
#             intent = "product_selection"

#         # 🎯 PRIORITY 4: IMAGE GENERATION REQUEST (User asks for creation without a base image)
#         elif any(k in message_lower for k in ["generate", "create", "make", "mockup", "design karke do", "bana do"]):
#             intent = "image_request"
        
#         # 🎯 PRIORITY 5: COMPANY INFO 
#         elif any(k in message_lower for k in ["company", "service", "about", "who are you", "kaam kya hai"]):
#             intent = "company_info"
        

#         print(f"🎯 Detected intent: {intent}")

#         # =========================================================================
#         # ✅ HANDLER 1: UI Product Change Notification (NEW)
#         # =========================================================================
#         if intent == "product_change_notification":
#             found_product = product_name.replace('_', ' ').title()
            
#             # Message is sent when user changes product in the UI
#             reply = (
#                 f"**You have changed the product selection to {found_product}!** Excellent. Here are the next steps for your new design:\n\n"
                
#                 "1. **Choose Sub-Product/Variant:** If **{found_product}** has different types (like 'single wall' or 'with lid'), please select the variant in the UI.\n\n"
                
#                 "2. **Select Color:** Next, please choose a **color** from the palette or press the **'Suggest by AI'** button for AI color recommendations.\n\n"
                
#                 "3. **Upload Logo or Type Brand Name:** Please use the **'Upload Logo'** button to add your logo. If you don't have a logo, you can **type your brand name in the chat** and we'll guide you on the next step.\n\n"
                
#                 "4. **Generate Mockup:** Once all selections are made, hit the **'Generate Mockup'** button! I am ready to instantly edit your design with commands like **'make it glossy'** or **'change color to pink'**."
#             )
#             return jsonify({"message": reply})


#         # =========================================================================
#         # ✅ HANDLER 2: Conversational Product Selection (UPDATED)
#         # =========================================================================
#         elif intent == "product_selection":
#             product_list = [name.replace('_', ' ').title() for name in PRODUCT_MAP.keys()]
#             product_list_str = ", ".join(product_list)
            
#             found_product = None
#             for key in PRODUCT_MAP.keys():
#                 if key.lower() in message_lower or key.replace('_', ' ').lower() in message_lower:
#                     found_product = key.replace('_', ' ').title()
#                     break

#             if found_product:
#                 # Message is sent when user types the product name in chat
#                 reply = (
#                     f"Thank you for choosing **{found_product}**! That is a great choice. "
#                     "Here are the next steps to quickly create your design:\n\n"
                    
#                     "1. **Choose Sub-Product/Variant:** If **{found_product}** has different types (like 'single wall' or 'with lid'), please select the variant in the UI.\n\n"
                    
#                     "2. **Select Color:** Next, please choose a **color** from the palette or press the **'Suggest by AI'** button for AI color recommendations.\n\n"
                    
#                     "3. **Upload Logo or Type Brand Name:** Please use the **'Upload Logo'** button to add your logo. If you don't have a logo, you can **type your brand name in the chat** and we'll guide you on the next step.\n\n"
                    
#                     "4. **Generate Mockup:** Once all selections are made, hit the **'Generate Mockup'** button! I am ready to instantly edit your design with commands like **'make it glossy'** or **'change color to pink'**."
#                 )
            
#             elif 'select the product for me' in message_lower or 'product batao' in message_lower:
#                 reply = (
#                     "I can certainly help you! We have many packaging options available.\n"
#                     "You can choose any of the following **Products** (just tell me the name):\n\n"
#                     f"**Available Products:** {product_list_str}.\n\n"
#                     "Which product would you like to design? E.g.: **'Paper Cup'** or **'Pizza Box'**? Tell me the name, or select it in the UI."
#                 )
#             else:
#                  reply = (
#                     "You need help choosing a product. Please tell me the name of a product (e.g., 'Paper Cup') from the list, or select one in the user interface."
#                 )

#             return jsonify({"message": reply})

#         # --- HANDLER 3: New Image Generation Request (Packify-Style Instructions) ---
#         elif intent == "image_request":
#             instruction_reply = (
#                 "Absolutely! **You must first complete the steps in the UI**:\n"
#                 "1. **Select the Product**.\n"
#                 "2. **Select Color** or get an **AI Suggestion**.\n"
#                 "3. **Upload Logo** or **Type Brand Name** in chat.\n"
#                 "4. Click the **'Generate Mockup'** button.\n\n"
#                 "I can only edit your design after the image is generated, for example, by asking me to **'make it glossy'**."
#             )
#             return jsonify({"message": instruction_reply})

#         # --- HANDLER 4: Image Edit Request (For automatic changes as requested by user) ---
#         elif intent == "image_edit":
#             if not image_b64:
#                  return jsonify({"message": "I need the current mockup image to apply your requested edit. Please upload a logo and generate a base mockup first."})
                 
#             edit_prompt = f"Apply the following change to the existing packaging design: {user_message}"
#             print(f"🪄 Image edit prompt: {edit_prompt}")

#             try:
#                 # NOTE: This calls the placeholder function defined above. You must ensure 'image_edit_ai' is defined.
#                 edited_image_data_url = image_edit_ai(edit_prompt, image_b64=image_b64, image_mime=image_mime)

#                 if not edited_image_data_url:
#                     # User-friendly failure response instead of technical error
#                     response_text = (
#                         "I couldn't process that specific image edit at this moment. "
#                         "Could you please try a simpler request, like 'make it glossy' or 'change the logo color to white'? "
#                         "I'm here to help you refine your design!"
#                     )
#                     return jsonify({"message": response_text})

#                 # Success: Return the new image data
#                 return jsonify({
#                     "message": f"Here is the updated **{product_name}** design with your requested change. Let me know if you need any further refinements!",
#                     "edited_image": edited_image_data_url, 
#                     "status": "image_updated"
#                 })

#             except Exception as e:
#                 print(f"❌ Image Edit AI Exception: {e}")
#                 traceback.print_exc()
#                 # User-friendly response for any external API or connectivity issue
#                 return jsonify({
#                     "message": "I'm experiencing a temporary issue connecting to the design tool. Please try your edit request again, or try a different command!",
#                     "status": "error_friendly" 
#                 })

#         # --- HANDLER 5: Company Info ---
#         elif intent == "company_info":
#             product_list = [name.replace('_', ' ').title() for name in PRODUCT_MAP.keys()]
            
#             company_info = {
#                 "name": "Greenwich Packaging",
#                 "about": "We are Greenwich Packaging, a creative studio offering sustainable, customized branding and high-quality packaging mockups.",
#                 "services": ["Logo Printing", "3D Mockups", "Brand Strategy", "Packaging Consultation"]
#             }

#             if "product" in message_lower or "how many products" in message_lower:
#                 product_summary = f"{len(product_list)} unique packaging products. For example: {', '.join(product_list[:3])} and many more."
#                 reply = f"At **{company_info['name']}**, we offer {product_summary}. Which one are you interested in?"
#             elif "service" in message_lower:
#                 reply = f"We offer services like: {', '.join(company_info['services'])}. Our focus is on bringing your brand to life."
#             elif "about" in message_lower or "company" in message_lower:
#                 reply = company_info["about"]
#             else:
#                 reply = f"We are **{company_info['name']}** — specialists in premium and eco-friendly packaging design and mockups."

#             return jsonify({"message": reply})


#         # --- HANDLER 6: Default Design Chat ---
#         else:
#             system_instruction = (
#                 "You are an expert AI Packaging Design Assistant for Greenwich Packaging. Follow these rules strictly:\n\n"
#                 "1. ONLY discuss packaging design, branding, colors, materials, printing, and customization.\n"
#                 "2. Keep responses concise (3-5 sentences maximum) and highly professional.\n"
#                 f"3. Current context: Product = {product_name}, Selected Color = {color}\n"
#                 "4. Ask clarifying questions about finish (matte/glossy), typography, or layout when needed.\n"
#                 "5. **Crucially, actively encourage the user to use the 'Generate Mockup' button to create a base design first. Then, instruct them that they can use the chat for instant live edits (e.g., 'make it glossy', 'change font to bold') to refine their design, acting as their seamless design partner.**"
#             )

#             contents = [
#                 genai.types.Content(
#                     role='user' if msg['role'] == 'user' else 'model',
#                     parts=[genai.types.Part.from_text(text=msg['content'])]
#                 )
#                 for msg in chat_history[-10:]
#             ]
            
#             if not contents or contents[-1].role != 'user' or contents[-1].parts[0].text != user_message:
#                  contents.append(genai.types.Content(role='user', parts=[genai.types.Part.from_text(text=user_message)]))

#             print(f"🤖 Sending to Gemini | Messages in context: {len(contents)}")
#             print("🧠 Preparing to call Gemini model...")

#             # ✅ NEW CODE (Correct New SDK Usage)
#             try:
#                 # ⚠️ FIX: Replaced deprecated 'generation_config' dictionary with the new SDK's 
#                 # 'config' parameter and the genai.types.GenerateContentConfig class.
#                 response = chat_client.models.generate_content(
#                     model="gemini-2.5-flash",
#                     contents=contents, # Uses the corrected list of dictionaries
#                     config=genai.types.GenerateContentConfig(
#                         temperature=0.7,
#                         max_output_tokens=300,
#                         top_p=0.95,
#                         top_k=40
#                     )
#                 )

#                 if not response or not getattr(response, 'text', None):
#                     print("⚠ Gemini returned no text or empty response:", response)
#                     # return jsonify({"message": "Sorry, I'm having trouble understanding that request. Please try again."})
#                     return jsonify({"message": "Got it, plz click on genrate button to view the Mockup"
#                     "."})

#                 response_text = response.text.strip()
#                 print(f"✅ Response generated | Length: {len(response_text)} chars")
#                 return jsonify({"message": response_text})

#             except Exception as e:
#                 print(f"❌ Gemini API Exception: {e}")
#                 traceback.print_exc()
#                 return jsonify({
#                     # "message": "I'm experiencing some issues connecting to the AI service. Please try again shortly.",
#                     "message": "click the generate button .",
#                     "error": str(e)
#                 })

#     except Exception as e:
#         print(f"❌ Chat error: {e}")
#         traceback.print_exc()
#         return jsonify({
#             "error": f"Chat service error: {str(e)}",
#             "message": "plz chick on genearte button."
#         }), 200

#         # ---------------------------------------------------------------------
#         # 🧹 FIX:Reset chat history when a new product is selected
#         # ---------------------------------------------------------------------
#         last_product = None
#         for msg in reversed(chat_history):
#             if "Product:" in msg.get("content", ""):
#                 last_product = msg["content"].split("Product:")[-1].strip()
#                 break

#         if last_product and last_product.lower() != product_name.lower():
#             print(f"🧹 Product changed from {last_product} → {product_name}. Full chat reset triggered.")
#             chat_history = []
#             system_reset_message = f"Product changed: Now focusing only on {product_name}. Ignore all previous design prompts or instructions."
#             user_message = system_reset_message

#         # --- Intent Detection ---
#         message_lower = user_message.lower()
#         intent = "design_chat"
        
#         # Keywords for image generation/instruction request
#         image_request_keywords = ["generate", "create", "make", "image", "mockup", "photo", "mujhe", "karke do", "design karke do", "can you make", "how to make", "bana do", "tasveer bana"] 
        
#         # Keywords for image edit intent 
#         image_edit_keywords = ["shine", "gloss", "color", "matte", "texture", "background", "font", "text change", "make it", "change color", "make it shiny", "remove background", "pink", "blue", "red", "yellow", "metallic", "badal do", "rang", "chamak", "background hata do", "font badal", "edit", "modify"]

#         # ✅ NEW INTENT KEYWORDS for conversational product selection
#         product_selection_keywords = ["select the product for me", "choose product", "suggest a product", "kon sa product", "product batao", "product select karo", "product recommend", "konsa product", "kaun sa product"]
        
#         # 🎯 PRIORITY 1: IMAGE EDIT (High priority for live edits)
#         if any(k in message_lower for k in image_edit_keywords) and image_b64:
#             intent = "image_edit"
        
#         # 🎯 PRIORITY 2: NEW FEATURE - CONVERSATIONAL PRODUCT SELECTION (Handles user request to select product)
#         elif any(k in message_lower for k in product_selection_keywords) or ("product" in message_lower and "select" in message_lower):
#             intent = "product_selection"

#         # 🎯 PRIORITY 3: IMAGE GENERATION REQUEST (If user asks for creation without a base image)
#         elif any(k in message_lower for k in image_request_keywords):
#             intent = "image_request"
        
#         # 🎯 PRIORITY 4: COMPANY INFO (About the service/company)
#         elif any(k in message_lower for k in ["company", "service", "about", "who are you", "kaam kya hai"]):
#             intent = "company_info"
        
#         # 🎯 PRIORITY 5: OFF-TOPIC GUARDRAIL
#         non_packaging_keywords = ['weather', 'news', 'movie', 'recipe', 'code', 'programming', 'math problem', 'homework', 'joke', 'story', 'game', 'politics', 'sports', 'celebrity', 'stock', 'cryptocurrency']
#         if any(keyword in message_lower for keyword in non_packaging_keywords):
#             response_text = "I specialize only in packaging design. Please ask questions related to your packaging design, colors, materials, branding, or mockup customization."
#             return jsonify({"message": response_text})


#         print(f"🎯 Detected intent: {intent}")

#         # =========================================================================
#         # ✅ HANDLER 2: Conversational Product Selection 
#         # =========================================================================
#         if intent == "product_selection":
#             # Convert product keys to readable titles
#             product_list = [name.replace('_', ' ').title() for name in PRODUCT_MAP.keys()]
#             product_list_str = ", ".join(product_list)
            
#             # Check if the user named a specific product
#             found_product = None
#             for key in PRODUCT_MAP.keys():
#                 # Check for both key name and title name in the message
#                 if key.lower() in message_lower or key.replace('_', ' ').lower() in message_lower:
#                     found_product = key.replace('_', ' ').title()
#                     break

#             if found_product:
#                 # If a product is mentioned, guide the user to confirm selection in the UI.
#                 reply = (
#                     f"You've asked to select the **{found_product}**. Great choice! \n"
#                     "Please also select **{found_product}** from the **'Product Selection'** drop-down in the user interface (UI). \n"
#                     "Once selected, **Upload your Logo** and press the **'Generate Mockup'** button. \n"
#                     "I can then instantly edit your design with commands like **'make it glossy'** or **'change color to pink'**!"
#                 )
#             elif 'select the product for me' in message_lower or 'product batao' in message_lower:
#                 # If user asks for suggestions, give the list.
#                 reply = (
#                     "I can help you with that! We have many packaging options available.\n"
#                     "You can choose one of the following **Products** (just tell me the name):\n\n"
#                     f"**Available Products:** {product_list_str}.\n\n"
#                     "Which product would you like to design? E.g.: **'Paper Cup'** or **'Pizza Box'**? Tell me the name, or select it in the UI."
#                 )
#             else:
#                  # Default product selection guidance (should be caught by the above, but as a fallback)
#                  reply = (
#                     "You need help choosing a product. We have Paper Cups, Paper Bags, Pizza Boxes, and many more. "
#                     "Please tell me the name of a product (e.g., 'Paper Cup') from the list, or select one in the user interface."
#                 )

#             return jsonify({"message": reply})


#         # --- HANDLER 1: New Image Generation Request (Packify-Style Instructions) ---
#         elif intent == "image_request":
#             instruction_reply = (
#                 "Absolutely! To **generate your custom packaging image**, please follow these steps using the user interface:\n"
#                 "1. **Select your Product** from the product list (e.g., Paper Cup, Pizza Box).\n"
#                 "2. **Choose a Color** or select the **'AI' button** near the color picker to get AI-suggested colors.\n"
#                 "3. **Upload your Logo** using the 'Upload Logo' button.\n"
#                 "4. Finally, press the **'Generate Mockup'** button to see your custom design!\n\n"
#                 "I cannot generate the image directly from the chat, but I'm here to guide you through the process and refine the design after generation."
#             )
#             return jsonify({"message": instruction_reply})
        
#         # =========================================================================
#         # ✅ HANDLER 2: Conversational Product Selection (UPDATED)
#         # =========================================================================
#         if intent == "product_selection":
#             # Convert product keys to readable titles
#             product_list = [name.replace('_', ' ').title() for name in PRODUCT_MAP.keys()]
#             product_list_str = ", ".join(product_list)
            
#             # Check if the user named a specific product
#             found_product = None
#             for key in PRODUCT_MAP.keys():
#                 # Check for both key name and title name in the message
#                 if key.lower() in message_lower or key.replace('_', ' ').lower() in message_lower:
#                     # Found a specific product like 'paper cup'
#                     found_product = key.replace('_', ' ').title()
#                     break

#             if found_product:
#                 # If a product is mentioned, the bot gives the full sequential instruction flow.
#                 reply = (
#                     f"**{found_product}** select karne ke liye dhanyawad! Bahut achha chunav hai. "
#                     "Ab aage ke steps dekhiye jisse aapka design jaldi ban sake:\n\n"
                    
#                     "1. **Sub-Product/Variant Choose Karein:** Agar **{found_product}** ki aur koi type available hai (jaise 'single wall' ya 'with lid'), toh kripya use UI se select karein.\n\n"
                    
#                     "2. **Color Select Karein:** Bahut accha! Ab, kripya **color** palette se choose karein ya **'Suggest by AI'** button dabakar AI se color suggestion lein.\n\n"
                    
#                     "3. **Logo Upload/Name Batayein:** Uske baad, **'Upload Logo'** button se apna logo upload karein. Agar aapke paas logo nahi hai, toh **chat mein brand name type kar dein**, hum aapko aage guide karenge.\n\n"
                    
#                     "4. **Mockup Generate Karein:** Jab yeh sab ho jaaye, toh **'Generate Mockup'** button dabayein! Main aapke design ko **'make it glossy'** ya **'change color to pink'** jaise commands se turant edit karne ke liye ready hoon!"
#                 )
            
#             # This handles the case where the user simply asks "select the product for me" without naming one.
#             elif 'select the product for me' in message_lower or 'product batao' in message_lower:
#                 reply = (
#                     "Mai aapki madad kar sakta hoon! Humare paas packaging mein bahut saare options hain.\n"
#                     "Aap inmein se koi ek **Product** chun sakte hain (kewal naam bata dein):\n\n"
#                     f"**Available Products:** {product_list_str}.\n\n"
#                     "Aap kis product ke liye design banana chahte hain? Jaise: **'Paper Cup'** ya **'Pizza Box'**? Naam batayein, ya UI mein select karein."
#                 )
#             else:
#                  # Default product selection guidance (fallback)
#                  reply = (
#                     "Aapko product chunne mein madad chahiye. Humare paas Paper Cups, Paper Bags, Pizza Boxes, aur bahut kuch hai. "
#                     "Kripya list mein se koi ek product (jaise: 'Paper Cup') chun kar mujhe batayein, ya user interface mein select karein."
#                 )

#             return jsonify({"message": reply})

        
#         # --- HANDLER 3: Image Edit Request (For automatic changes as requested by user) ---
#         elif intent == "image_edit":
#             if not image_b64:
#                  return jsonify({"message": "I need the current mockup image to apply your requested edit. Please upload a logo and generate a base mockup first."})
                 
#             edit_prompt = f"Apply the following change to the existing packaging design: {user_message}"
#             print(f"🪄 Image edit prompt: {edit_prompt}")

#             try:
#                 # NOTE: This calls the placeholder function defined above. You must ensure 'image_edit_ai' is defined.
#                 edited_image_data_url = image_edit_ai(edit_prompt, image_b64=image_b64, image_mime=image_mime)

#                 if not edited_image_data_url:
#                     # User-friendly failure response instead of technical error
#                     response_text = (
#                         "I couldn't process that specific image edit at this moment. "
#                         "Could you please try a simpler request, like 'make it glossy' or 'change the logo color to white'? "
#                         "I'm here to help you refine your design!"
#                     )
#                     return jsonify({"message": response_text})

#                 # Success: Return the new image data
#                 return jsonify({
#                     "message": f"Here is the updated **{product_name}** design with your requested change. Let me know if you need any further refinements!",
#                     "edited_image": edited_image_data_url, 
#                     "status": "image_updated"
#                 })

#             except Exception as e:
#                 print(f"❌ Image Edit AI Exception: {e}")
#                 traceback.print_exc()
#                 # User-friendly response for any external API or connectivity issue
#                 return jsonify({
#                     "message": "I'm experiencing a temporary issue connecting to the design tool. Please try your edit request again, or try a different command!",
#                     "status": "error_friendly" # Use a friendly status flag if needed on the frontend
#                 })

#         # --- HANDLER 4: Company Info ---
#         elif intent == "company_info":
#             product_list = [name.replace('_', ' ').title() for name in PRODUCT_MAP.keys()]
            
#             company_info = {
#                 "name": "Greenwich Packaging",
#                 "about": "We are Greenwich Packaging, a creative studio offering sustainable, customized branding and high-quality packaging mockups.",
#                 "services": ["Logo Printing", "3D Mockups", "Brand Strategy", "Packaging Consultation"]
#             }

#             if "product" in message_lower or "how many products" in message_lower:
#                 product_summary = f"{len(product_list)} unique packaging products. For example: {', '.join(product_list[:3])} and many more."
#                 reply = f"At **{company_info['name']}**, we offer {product_summary}. Which one are you interested in?"
#             elif "service" in message_lower:
#                 reply = f"We offer services like: {', '.join(company_info['services'])}. Our focus is on bringing your brand to life."
#             elif "about" in message_lower or "company" in message_lower:
#                 reply = company_info["about"]
#             else:
#                 reply = f"We are **{company_info['name']}** — specialists in premium and eco-friendly packaging design and mockups."

#             return jsonify({"message": reply})

#         # --- HANDLER 5: Default Design Chat ---
#         # --- HANDLER 5: Default Design Chat (Polished & Polite AI Personality) ---
#     else:
#     # Define a clear system personality
#         system_prompt = f"""
#     You are a professional, friendly, and creative AI Packaging Design Assistant for Greenwich Packaging.

#     ✳️ Core Behavior:
#     - Always be polite, concise, and confident.
#     - If the user greets you (hi, hello, how are you), greet them warmly.
#     - If the user thanks you, reply kindly.
#     - Always stay within packaging, design, branding, materials, color, and mockup topics.
#     - Never show technical or API errors to the user.
#     - When confused, gently ask clarifying questions about their design.
#     - When user gives a design instruction, confirm understanding and guide them to click **‘Generate Mockup’**.

#     🧩 Context:
#     - Current product: {product_name}
#     - Selected color: {color}

#     🎯 Example tone:
#     “That sounds great! I’ll help you make this packaging look stunning. Please click the Generate Mockup button to apply it visually.”
#     """

#     # Build message history properly
#     messages = [{"role": "system", "parts": [{"text": system_prompt}]}]
#     for msg in chat_history[-10:]:
#         messages.append({
#             "role": "user" if msg["role"] == "user" else "model",
#             "parts": [{"text": msg["content"]}]
#         })

#     messages.append({"role": "user", "parts": [{"text": user_message}]})

#     print(f"🤖 Sending polite AI chat | Context: {len(messages)} messages")

#     # ✅ NEW CODE (Correct New SDK Usage)
#     try:
#         response = chat_client.models.generate_content(
#             model="gemini-2.5-flash",
#             contents=contents,  # Uses the corrected list of dictionaries
#             config=genai.types.GenerateContentConfig(
#                 temperature=0.7,
#                 max_output_tokens=300,
#                 top_p=0.95,
#                 top_k=40
#             )
#         )

#         if not response or not getattr(response, "text", None):
#             print("⚠ Gemini returned empty or no response.")
#             return jsonify({"message": "I'm here and ready to help you! Please tell me your packaging idea or click Generate Mockup."})

#         reply_text = response.text.strip()
#         print(f"✅ AI reply: {reply_text[:120]}...")
#         return jsonify({"message": reply_text})

#     except Exception as e:
#         print(f"❌ Gemini Exception: {e}")
#         traceback.print_exc()
#         return jsonify({
#             "message": "I’m having a small issue responding right now, but you can still use the Generate Mockup button.",
#             "error": str(e)
#         })
#         traceback.print_exc()
#         return jsonify({
#             "message": "I’m having a small issue responding right now, but you can still use the Generate Mockup button.",
#             "error": str(e)
#         })
    

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
# # ✅ SMART CHATBOT
# # =========================================================================
@app.route('/send_chat', methods=['POST'])
def send_chat():
    """Smart chatbot that understands edit requests, product changes, and design chat."""
    global PRODUCT_MAP

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

        print(f"📨 Chat request received | Current Product: {product_name} | Color: {color}")
        print(f"💬 User message: {user_message[:200]}")

        last_product = None
        for msg in reversed(chat_history):
            if "Product:" in msg.get("content", ""):
                last_product = msg["content"].split("Product:")[-1].strip()
                break

        product_changed = False
        if last_product and last_product.lower() != product_name.lower():
            product_changed = True
            print(f"🧹 Product changed from {last_product} → {product_name}. Full chat reset triggered.")
            chat_history = []
            system_reset_message = f"Product changed: Now focusing only on {product_name}. Ignore all previous design prompts or instructions."
            user_message = system_reset_message

        message_lower = user_message.lower()
        intent = "design_chat"
        
        image_edit_keywords = ["shine", "gloss", "color", "matte", "texture", "background", "font", "make it", "change color", "edit", "modify"]
        product_selection_keywords = ["select the product for me", "choose product", "suggest a product", "kon sa product", "product batao", "product select karo", "product recommend", "konsa product", "kaun sa product"]
        
        is_product_selection_query = any(k in message_lower for k in product_selection_keywords) or ("product" in message_lower and "select" in message_lower)

        if product_changed and not is_product_selection_query:
            intent = "product_change_notification"
        elif any(k in message_lower for k in image_edit_keywords) and image_b64:
            intent = "image_edit"
        elif is_product_selection_query:
            intent = "product_selection"
        elif any(k in message_lower for k in ["generate", "create", "make", "mockup", "design karke do", "bana do"]):
            intent = "image_request"
        elif any(k in message_lower for k in ["company", "service", "about", "who are you", "kaam kya hai"]):
            intent = "company_info"

        print(f"🎯 Detected intent: {intent}")

        if intent == "product_change_notification":
            found_product = product_name.replace('_', ' ').title()
            
            reply = (
                f"**You have changed the product selection to {found_product}!** Excellent. Here are the next steps for your new design:\n\n"
                "1. **Choose Sub-Product/Variant:** If this product has different types, please select the variant in the UI.\n\n"
                "2. **Select Color:** Next, please choose a **color** from the palette or press the **'Suggest by AI'** button for AI color recommendations.\n\n"
                "3. **Upload Logo or Type Brand Name:** Please use the **'Upload Logo'** button to add your logo. If you don't have a logo, you can **type your brand name in the chat** and we'll guide you on the next step.\n\n"
                "4. **Generate Mockup:** Once all selections are made, hit the **'Generate Mockup'** button! I am ready to instantly edit your design with commands like **'make it glossy'** or **'change color to pink'**."
            )
            return jsonify({"message": reply})

        elif intent == "product_selection":
            product_list = [name.replace('_', ' ').title() for name in PRODUCT_MAP.keys()]
            product_list_str = ", ".join(product_list)
            
            found_product = None
            for key in PRODUCT_MAP.keys():
                if key.lower() in message_lower or key.replace('_', ' ').lower() in message_lower:
                    found_product = key.replace('_', ' ').title()
                    break

            if found_product:
                reply = (
                    f"Thank you for choosing **{found_product}**! That is a great choice. "
                    "Here are the next steps to quickly create your design:\n\n"
                    "1. **Choose Sub-Product/Variant:** If this product has different types, please select the variant in the UI.\n\n"
                    "2. **Select Color:** Next, please choose a **color** from the palette or press the **'Suggest by AI'** button for AI color recommendations.\n\n"
                    "3. **Upload Logo or Type Brand Name:** Please use the **'Upload Logo'** button to add your logo. If you don't have a logo, you can **type your brand name in the chat** and we'll guide you on the next step.\n\n"
                    "4. **Generate Mockup:** Once all selections are made, hit the **'Generate Mockup'** button! I am ready to instantly edit your design with commands like **'make it glossy'** or **'change color to pink'**."
                )
            elif 'select the product for me' in message_lower or 'product batao' in message_lower:
                reply = (
                    "I can certainly help you! We have many packaging options available.\n"
                    "You can choose any of the following **Products** (just tell me the name):\n\n"
                    f"**Available Products:** {product_list_str}.\n\n"
                    "Which product would you like to design? E.g.: **'Paper Cup'** or **'Pizza Box'**? Tell me the name, or select it in the UI."
                )
            else:
                reply = (
                    "You need help choosing a product. Please tell me the name of a product (e.g., 'Paper Cup') from the list, or select one in the user interface."
                )

            return jsonify({"message": reply})

        elif intent == "image_request":
            instruction_reply = (
                "Absolutely! **You must first complete the steps in the UI**:\n"
                "1. **Select the Product**.\n"
                "2. **Select Color** or get an **AI Suggestion**.\n"
                "3. **Upload Logo** or **Type Brand Name** in chat.\n"
                "4. Click the **'Generate Mockup'** button.\n\n"
                "I can only edit your design after the image is generated, for example, by asking me to **'make it glossy'**."
            )
            return jsonify({"message": instruction_reply})

        elif intent == "image_edit":
            if not image_b64:
                return jsonify({"message": "I need the current mockup image to apply your requested edit. Please upload a logo and generate a base mockup first."})
                 
            edit_prompt = f"Apply the following change to the existing packaging design: {user_message}"
            print(f"🪄 Image edit prompt: {edit_prompt}")

            try:
                edited_image_data_url = image_edit_ai(edit_prompt, image_b64=image_b64, image_mime=image_mime)

                if not edited_image_data_url:
                    response_text = (
                        "I couldn't process that specific image edit at this moment. "
                        "Could you please try a simpler request, like 'make it glossy' or 'change the logo color to white'? "
                        "I'm here to help you refine your design!"
                    )
                    return jsonify({"message": response_text})

                return jsonify({
                    "message": f"Here is the updated **{product_name}** design with your requested change. Let me know if you need any further refinements!",
                    "edited_image": edited_image_data_url, 
                    "status": "image_updated"
                })

            except Exception as e:
                print(f"❌ Image Edit AI Exception: {e}")
                traceback.print_exc()
                return jsonify({
                    "message": "I'm experiencing a temporary issue connecting to the design tool. Please try your edit request again, or try a different command!",
                    "status": "error_friendly" 
                })

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
                reply = f"We are **{company_info['name']}** – specialists in premium and eco-friendly packaging design and mockups."

            return jsonify({"message": reply})

        else:
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
                    print("⚠️ Gemini returned no text or empty response:", response)
                    return jsonify({"message": "Well, on the left side, please click on generate button."})

                response_text = response.text.strip()
                print(f"✅ Response generated | Length: {len(response_text)} chars")
                return jsonify({"message": response_text})

            except Exception as e:
                print(f"❌ Gemini API Exception: {e}")
                traceback.print_exc()
                return jsonify({
                    "message": "Click the generate button.",
                    "error": str(e)
                })

    except Exception as e:
        print(f"❌ Chat error: {e}")
        traceback.print_exc()
        return jsonify({
            "error": f"Chat service error: {str(e)}",
            "message": "Please click on generate button."
        }), 200

def image_edit_ai(prompt, image_b64=None, image_mime="image/png"):
    """Call Gemini image API to edit an existing image using prompt."""
    try:
        print(f"🎨 image_edit_ai called | has_image={bool(image_b64)} | prompt_len={len(prompt)}")

        parts_list = []
        parts_list.append({"text": prompt})

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

        first_candidate = candidates[0]
        parts = first_candidate.get("content", {}).get("parts", [])
        if not parts or "inlineData" not in parts[0]:
            print("❌ inlineData missing in Gemini image response parts. Possibly blocked by safety filter.")
            return None

        img_b64 = parts[0]["inlineData"]["data"]
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

        brand_name = data.get("brand_name", "").strip()

        if not logo_b64 and not brand_name:
            print("⚠️ No logo and no brand name: using default Greenwich logo.")
            default_logo_path = os.path.join(app.root_path, 'static', 'default_logo.png')
            try:
                with open(default_logo_path, "rb") as image_file:
                    logo_b64 = base64.b64encode(image_file.read()).decode('utf-8')
                    logo_mime_type = 'image/png'
            except FileNotFoundError:
                print(f"❌ Default logo file not found at {default_logo_path}")
                # Continue with no logo if default is missing
        user_design_prompt = data.get("design_prompt", "").strip() 
        # Get brand name from request
        brand_name = data.get("brand_name", "").strip()
        print(f"   Brand Name: {brand_name}")
        selected_color = data.get("color", "default color").strip()
        
        print(f"🎨 Mockup Generation Request:")
        print(f"   Product: main={main_product_id}, sub={sub_product_id}, final={product_id}")
        print(f"   Color: {selected_color}")
        print(f"   Logo: {bool(logo_b64)}")
        print(f"   Design Prompt: {user_design_prompt[:100] if user_design_prompt else 'None'}...")
        
        if not product_id:
            return jsonify({"error": "No product selected."}), 400
        
        # ✅ Handle PDF conversion
        # âœ… Handle ALL format conversions (PDF, GIF, WEBP, etc.)
        original_mime_type = logo_mime_type
        if logo_b64 and logo_mime_type:
            # Convert any non-standard format to PNG
            if logo_mime_type not in ['image/png', 'image/jpeg', 'image/jpg']:
                print(f"📝 Converting logo from {logo_mime_type} to PNG...")
                logo_b64, logo_mime_type = convert_logo_format(logo_b64, logo_mime_type)
        
        # ✅ Upload logo to Drive FIRST
        logo_drive_url = ""
        
        if logo_b64 and logo_mime_type:
            print(f"📁 Logo detected: mime_type={logo_mime_type}, data_length={len(logo_b64)}")
            
            try:
                logo_data = base64.b64decode(logo_b64)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Determine file extension based on ORIGINAL mime type
                # âœ… Determine file extension based on ORIGINAL mime type
                ext_map = {
                    "image/png": "png",
                    "image/jpeg": "jpg",
                    "image/jpg": "jpg",
                    "application/pdf": "png",
                    "image/gif": "png",
                    "image/webp": "png",
                    "image/avif": "png",
                    "image/bmp": "png",
                    "image/tiff": "png",
                    "image/tif": "png",
                    "image/svg+xml": "png"
                }
                ext = ext_map.get(original_mime_type, "png")
                
                logo_filename = f"logo_{product_id}_{timestamp}.{ext}"
                
                print(f"📤 Uploading logo to Drive: {logo_filename} (size: {len(logo_data)} bytes)")
                
                # Upload with CURRENT mime type (after conversion) logo_drive_url = upload_to_drive(logo_data, logo_filename, logo_mime_type)
                
                
                
                    
            except Exception as logo_error:
                print(f"❌ Logo upload error: {logo_error}")
                traceback.print_exc()
        else:
            print(f"ℹ️ No logo to upload: logo_b64={bool(logo_b64)}, mime_type={logo_mime_type}")

        # Get product image
        product_image_path = os.path.join(app.root_path, PRODUCT_MAP.get(product_id))
        
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

# Construct final request prompt
        image_request_prompt = base_prompt

# ✅ NEW LOGIC: Handle logo + brand name combination (as requested by user)
        if logo_b64 and brand_name:
    # Both logo and brand name provided
            image_request_prompt += f" Use the uploaded logo prominently on the design AND also include the brand name '{brand_name}' text in a complementary elegant font near the logo. The text should be integrated into the design, for example, as a tagline or a secondary branding element."
        elif logo_b64 and not brand_name:
    # Only logo provided
            image_request_prompt += " Blend the second image (logo) naturally onto the product surface with realistic lighting and perspective. The design should focus only on the logo and complementary patterns."
        elif not logo_b64 and brand_name:
    # Only brand name provided (NO LOGO)
            image_request_prompt += f" Since no logo is provided, create an elegant typographic design featuring the brand name '{brand_name}' as the main visual element. Use a premium, modern font style that matches the packaging aesthetic. The brand name must be clearly visible and centered on the product. Add subtle decorative elements around the text if appropriate."
        else:
    # Neither logo nor brand name (fallback)
            image_request_prompt   += " Generate an attractive generic design with modern patterns suitable for the product. No logo or brand name should be visible."

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
        
        
        return jsonify({
            "image_b64": img_b64,
            "message": "Mockup generated successfully!",
            "logo_drive_url": logo_drive_url if 'logo_drive_url' in locals() else ""
})

    except Exception as e:
        print(f"❌ Mockup generation error: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# =========================================================================
# ✅ WATERMARK FUNCTION
# =========================================================================
# def add_watermark(image_data):
#     """Adds a text watermark to the image."""
#     try:
#         img = Image.open(BytesIO(image_data)).convert("RGBA")
#         # draw = ImageDraw.Draw(img)
        
#         watermark_text = "created by - www.greenwichpackaing.co.uk"
        
#         # Determine font size based on image size
#         width, height = img.size
#         font_size = int(height / 40) # Approximately 2.5% of height
        
#         # Try to use a common font, or default to PIL's built-in font
#         try:
#             # Assuming a common font like Arial or a generic sans-serif is available
#             # If not, this will raise an OSError and fall back to the default font
#             font = ImageFont.truetype("arial.ttf", font_size)
#         except IOError:
#             font = ImageFont.load_default()
#             font_size = 10 # Reset font size for default font

#         # Position the watermark (bottom right corner)
#         text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
#         text_width = text_bbox[2] - text_bbox[0]
#         text_height = text_bbox[3] - text_bbox[1]
        
#         margin = 10
#         x = width - text_width - margin
#         y = height - text_height - margin
        
#         # Add a semi-transparent background box for better readability
#         # The box is slightly larger than the text
#         box_margin = 5
#         draw.rectangle(
#             [
#                 x - box_margin, 
#                 y - box_margin, 
#                 x + text_width + box_margin, 
#                 y + text_height + box_margin
#             ], 
#             fill=(0, 0, 0, 128) # Semi-transparent black
#         )
        
#         # Draw the text
#         draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 255)) # White text
        
#         # Save the watermarked image to a BytesIO object
#         output = BytesIO()
#         img.save(output, format="PNG")
#         output.seek(0)
#         return output

#     except Exception as e:
#         print(f"❌ Watermark error: {e}")
#         traceback.print_exc()
#         # Return original image data if watermarking fails
#         return BytesIO(image_data)

def add_watermark(image_data):
    """Adds a transparent green watermark + company logo."""
    try:
        img = Image.open(BytesIO(image_data)).convert("RGBA")

        # Create transparent overlay
        watermark_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(watermark_layer)

        watermark_text = "www.greenwichpackaging.co.uk"

        width, height = img.size
        font_size = int(height / 35)   # Bigger & more premium

        # --- Premium font (try) ---
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        # --- Text size ---
        text_bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        margin = 20
        x = width - text_width - margin
        y = height - text_height - margin

        # --- Green text ---
        green_color = (0, 140, 0, 255)

        draw.text((x, y), watermark_text, font=font, fill=green_color)

        # -----------------------------------------------------
        # ⭐ Add Company Logo (left bottom - opposite of text)
        # -----------------------------------------------------
        try:
            logo = Image.open("static/logo.jpeg").convert("RGBA")

            # Resize logo relative to image height
            logo_h = int(height / 5)  # Adjust size (10% height)
            logo_w = int(logo.width * (logo_h / logo.height))
            logo = logo.resize((logo_w, logo_h), Image.LANCZOS)

            # Logo position (bottom-left)
            logo_x = margin
            logo_y = height - logo_h - margin

            watermark_layer.paste(logo, (logo_x, logo_y), logo)
        except Exception as logo_err:
            print("⚠️ Logo not added:", logo_err)

        # --- Merge watermark layer ---
        final_img = Image.alpha_composite(img, watermark_layer)

        output = BytesIO()
        final_img.save(output, format="PNG")
        output.seek(0)
        return output

    except Exception as e:
        print(f"❌ Watermark error: {e}")
        return BytesIO(image_data)

@app.route("/download_mockup", methods=["POST"])
def download_mockup():
    """✅ Takes base64 image, creates PDF with 3 pages: cover, mockup, description"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        
        data = request.get_json()
        image_b64 = data.get("image_b64")
        filename = data.get("filename", "mockup_design.pdf")  # Changed to .pdf
        email = data.get("email", "").strip()
        phone = data.get("phone", "").strip()
        brand_name = data.get("brand_name", "").strip()

        if not image_b64:
            return jsonify({"error": "Missing image data"}), 400

        # Validate email and phone
        if not validate_email(email):
            return jsonify({"error": "Invalid email address"}), 400
        
        if not validate_international_phone(phone):
            return jsonify({"error": "Invalid phone number"}), 400

        # 1. Decode Base64
        if "," in image_b64:
            image_b64 = image_b64.split(",")[1]
            
        image_data = base64.b64decode(image_b64)

        # 2. Add Watermark to image
        watermarked_image_stream = add_watermark(image_data)
        watermarked_image_stream.seek(0)
        watermarked_image = Image.open(watermarked_image_stream)
        
        # 3. Create PDF with 3 pages
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=A4)
        width, height = A4
        
        # Define colors
        green = HexColor('#00B050')
        white = HexColor('#FFFFFF')
        black = HexColor('#1A1A1A')
        
        # ================================================================
        # PAGE 1: COVER PAGE WITH GREENWICH LOGO
        # ================================================================
        c.setFillColor(white)
        c.rect(0, 0, width, height, fill=True, stroke=False)
        
        # Top Green Bar
        c.setFillColor(green)
        c.rect(0, height - 100, width, 100, fill=True, stroke=False)
        
        # Greenwich Logo
        try:
            greenwich_logo_path = os.path.join(app.root_path, 'static', 'gp-logo.png')
            if os.path.exists(greenwich_logo_path):
                c.drawImage(greenwich_logo_path, 
                           (width - 200) / 2, height / 2 + 50,
                           width=200, height=200,
                           preserveAspectRatio=True, mask='auto')
        except Exception as logo_err:
            print(f"⚠️ Logo load error: {logo_err}")
        
        # Main Title
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 48)
        c.drawCentredString(width/2, height / 2 - 80, "YOUR MOCKUP")
        c.drawCentredString(width/2, height / 2 - 130, "DESIGN")
        
        # Brand Name
        if brand_name:
            c.setFont("Helvetica-Bold", 20)
            c.drawCentredString(width/2, height / 2 - 180, brand_name.upper())
        
        # Footer
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, 80, "Greenwich Packaging - Premium Design Studio")
        c.drawCentredString(width/2, 60, datetime.now().strftime('%d %B %Y'))
        
        c.showPage()
        
        # ================================================================
        # PAGE 2: MOCKUP IMAGE WITH WATERMARK
        # ================================================================
        c.setFillColor(white)
        c.rect(0, 0, width, height, fill=True, stroke=False)
        
        # Header
        c.setFillColor(green)
        c.rect(0, height - 60, width, 60, fill=True, stroke=False)
        
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width/2, height - 38, "YOUR CUSTOM DESIGN")
        
        # Draw watermarked mockup image (centered, fit to page)
        try:
            if watermarked_image.mode != 'RGB':
                watermarked_image = watermarked_image.convert('RGB')
            
            img_buffer = io.BytesIO()
            watermarked_image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Calculate dimensions to fit
            img_width = width - 80  # 40px margin on each side
            img_height = height - 180  # Space for header and footer
            
            c.drawImage(ImageReader(img_buffer), 
                       40, 100,
                       width=img_width, height=img_height,
                       preserveAspectRatio=True, mask='auto')
        except Exception as img_err:
            print(f"❌ Image render error: {img_err}")
        
        # Footer
        c.setFont("Helvetica", 9)
        c.drawCentredString(width/2, 40, f"Design created for: {brand_name if brand_name else email}")
        c.drawCentredString(width/2, 25, "www.greenwichpackaging.co.uk")
        
        c.showPage()
        
        # ================================================================
        # PAGE 3: DESCRIPTION PAGE
        # ================================================================
        c.setFillColor(white)
        c.rect(0, 0, width, height, fill=True, stroke=False)
        
        # Header
        c.setFillColor(green)
        c.rect(0, height - 60, width, 60, fill=True, stroke=False)
        
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width/2, height - 38, "DESIGN DETAILS")
        
        # Content
        c.setFillColor(black)
        y_position = height - 120
        
        # Brand Information
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y_position, "Brand Information:")
        y_position -= 30
        
        c.setFont("Helvetica", 12)
        c.drawString(70, y_position, f"Brand Name: {brand_name if brand_name else 'N/A'}")
        y_position -= 25
        c.drawString(70, y_position, f"Contact Email: {email}")
        y_position -= 25
        c.drawString(70, y_position, f"Phone: {phone}")
        y_position -= 40
        
        # Design Features
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y_position, "Design Features:")
        y_position -= 30
        
        c.setFont("Helvetica", 12)
        features = [
            "✓ High-resolution AI-generated mockup",
            "✓ Professional watermarked preview",
            "✓ Custom branding integration",
            "✓ Ready for production review",
            "✓ Premium packaging design"
        ]
        
        for feature in features:
            c.drawString(70, y_position, feature)
            y_position -= 22
        
        y_position -= 30
        
        # Next Steps
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y_position, "Next Steps:")
        y_position -= 30
        
        c.setFont("Helvetica", 12)
        steps = [
            "1. Review your design carefully",
            "2. Contact us for high-resolution unwatermarked files",
            "3. Request modifications or approve for production",
            "4. Place bulk order for printing"
        ]
        
        for step in steps:
            c.drawString(70, y_position, step)
            y_position -= 22
        
        # Contact Box at bottom
        c.setFillColor(HexColor('#F0F0F0'))
        c.rect(40, 60, width - 80, 80, fill=True, stroke=False)
        
        c.setFillColor(green)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width/2, 115, "GREENWICH PACKAGING")
        
        c.setFillColor(black)
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, 95, "📧 info@greenwichpackaging.co.uk")
        c.drawCentredString(width/2, 80, "🌐 www.greenwichpackaging.co.uk")
        c.drawCentredString(width/2, 65, "📞 Contact us for bulk orders and customization")
        
        c.save()
        pdf_buffer.seek(0)
        
        # 4. Send Welcome Email (in background)
        send_welcome_email(email, brand_name)
        
        # Ensure filename ends with .pdf
        if not filename.endswith('.pdf'):
            filename = filename.rsplit('.', 1)[0] + '.pdf'
        
        print(f"✅ PDF created with 3 pages for {email}")

        # 5. Return PDF file
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"❌ Download PDF error: {e}")
        traceback.print_exc()
        return jsonify({"error": "Could not process download"}), 500
# email verification regex
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_welcome_email_async(app, recipient_email, brand_name):
    """Send welcome email using direct SMTP"""
    try:
        # Email credentials
        sender_email = os.environ.get('EMAIL_USER')
        sender_password = os.environ.get('EMAIL_PASSWORD')
        
        if not sender_email or not sender_password:
            print("❌ Email credentials not configured")
            return
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "🎨 Welcome to Greenwich Packaging - Your Mockup is Ready!"
        msg['From'] = sender_email
        msg['To'] = recipient_email
        
        # HTML body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f7fff5; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 40px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #6a994e, #5d8845); padding: 30px; text-align: center; color: white; }}
                .content {{ padding: 30px; }}
                .button {{ display: inline-block; background: #6a994e; color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; margin: 20px 0; }}
                .footer {{ background: #f0f0f0; padding: 20px; text-align: center; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Thank You for Choosing Greenwich Packaging!</h1>
                </div>
                <div class="content">
                    <h2>Hello{' ' + brand_name if brand_name else ''}! 👋</h2>
                    <p>Thank you for downloading your mockup design. We hope you liked the design and found it useful for your project.</p>
                    
                    <p>We're glad you chose our platform to create your mockup. Our goal is to make your design process faster, easier, and more creative.</p>
                    
                    <h3>What's Next?</h3>
                    <ul>
                        <li>✅ Your mockup has been successfully generated</li>
                        <li>🎨 Need changes? Chat with our AI assistant</li>
                        <li>📦 Ready to print? Contact us for bulk orders</li>
                    </ul>
                    
                    <p>If you need any help, changes, or have feedback, feel free to reach out anytime. We'd love to hear from you.</p>
                    
                    <p style="text-align: center;">
                        <a href="https://www.greenwichpackaging.co.uk" class="button">Visit Our Website</a>
                    </p>
                    
                    <p><strong>Happy designing! 🎨</strong></p>
                </div>
                <div class="footer">
                    <p>Warm regards,<br><strong>Team Greenwich Packaging</strong></p>
                    <p>📧 info@greenwichpackaging.co.uk | 🌐 www.greenwichpackaging.co.uk</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Attach HTML
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        print(f"✅ Welcome email sent to {recipient_email}")
        
    except Exception as e:
        print(f"❌ Email send error: {e}")
        traceback.print_exc()

def send_welcome_email(recipient_email, brand_name=""):
    """Trigger email sending in background"""
    thread = threading.Thread(
        target=send_welcome_email_async, 
        args=(app, recipient_email, brand_name)
    )
    thread.start()


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



# =========================================================================
# 🗄️ DATABASE WITH USER ISOLATION
# =========================================================================
DB_FILE = "chat_history.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Check if user_id column exists in chats, if not, we need to migrate or recreate
    # For simplicity in this update, we will create if not exists, 
    # but strictly ensuring the schema is correct.
    
    c.execute('''CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,  -- 👈 Added User ID column
                    title TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )''')
                
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    role TEXT,
                    content TEXT,
                    image TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(chat_id) REFERENCES chats(id)
                )''')
    
    # 🛠️ MIGRATION HELPER: If you already have a DB without user_id, 
    # this quick hack ensures the column exists without deleting data.
    try:
        c.execute("ALTER TABLE chats ADD COLUMN user_id TEXT")
    except sqlite3.OperationalError:
        pass # Column likely already exists
    
    # ✅ Create Mockup History Table (For Library)
    c.execute('''CREATE TABLE IF NOT EXISTS mockup_history (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    product TEXT,
                    brand_name TEXT,
                    color TEXT,
                    logo_path TEXT,
                    generated_image_path TEXT,
                    thumbnail_path TEXT,
                    chat_id INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )''')

    conn.commit()
    conn.close()

init_db()

# =========================================================================
# 🔄 CHAT ROUTES (UPDATED FOR USER ISOLATION)
# =========================================================================

@app.route('/chats', methods=['GET', 'POST'])
def manage_chats():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # 🔑 Get User ID from headers (sent by frontend)
    user_id = request.headers.get('X-User-ID')

    if not user_id:
        return jsonify({"error": "User ID required"}), 400

    if request.method == 'POST':
        # Create a new chat specifically for this user
        data = request.json
        title = data.get('title', 'New Chat')
        
        c.execute("INSERT INTO chats (user_id, title) VALUES (?, ?)", (user_id, title))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        return jsonify({"id": new_id, "title": title})

    # GET: Return ONLY chats belonging to this user
    c.execute("SELECT id, title, created_at FROM chats WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    chats = [{"id": row[0], "title": row[1], "created_at": row[2]} for row in c.fetchall()]
    conn.close()
    return jsonify(chats)



@app.route('/chats/<int:chat_id>', methods=['GET'])
def get_chat(chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT role, content, image FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))
    messages = []
    for row in c.fetchall():
        msg = {"role": row[0], "content": row[1]}
        if row[2]:
            msg["image"] = row[2]
        messages.append(msg)
    conn.close()
    return jsonify(messages)


@app.route('/chats/<int:chat_id>/context', methods=['GET'])
def get_chat_context(chat_id):
    """Retrieves the latest product and image context for a given chat ID."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Get the latest mockup saved for this chat
    c.execute("""
        SELECT product, brand_name, color, generated_image_path
        FROM mockup_history
        WHERE chat_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (chat_id,))
    
    row = c.fetchone()
    conn.close()
    
    if row:
        product, brand_name, color, generated_image_path = row
        
        # Check if the product is a sub-product (e.g., 'flat' is a sub-product of 'paper_bag')
        # This logic is based on the assumption that sub-products are stored directly in the 'product' column
        # We need to determine the main product and sub-product from the stored 'product' value.
        # Since the mapping logic is complex, for now, we'll return the raw product and let the frontend handle the mapping.
        
        return jsonify({
            "status": "ok",
            "product": product,
            "brand_name": brand_name,
            "color": color,
            "generated_image": generated_image_path # This is the URL/path to the image
        })
    else:
        return jsonify({"status": "not_found", "message": "No context found for this chat."})


@app.route('/chats/<int:chat_id>/message', methods=['POST'])
def add_message(chat_id):
    data = request.json
    print("📩 Received message:", data)  # <-- add this line
    role = data.get("role")
    content = data.get("content", "")
    image = data.get("image", None)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (chat_id, role, content, image) VALUES (?, ?, ?, ?)",
        (chat_id, role, content, image),
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

@app.route('/chats/<int:chat_id>/title', methods=['POST'])
def update_chat_title(chat_id):
    data = request.json
    new_title = data.get('title', 'Untitled Chat')
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE chats SET title = ? WHERE id = ?", (new_title, chat_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "title": new_title})

@app.route('/chats/<int:chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    c.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})


@app.route('/chats/<int:chat_id>/rename', methods=['POST'])
def rename_chat(chat_id):
    data = request.json
    new_title = data.get('title', 'Untitled Chat')
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE chats SET title = ? WHERE id = ?", (new_title, chat_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "renamed", "title": new_title})



# =========================================================================
# 📸 PHOTO LIBRARY ROUTES (ADD THIS SECTION)
# =========================================================================

@app.route('/save-mockup-to-library', methods=['POST'])
def save_mockup_to_library():
    """Save generated mockup to library database"""
    try:
        data = request.json
        user_id = request.headers.get('X-User-ID', 'guest')
        
        product = data.get('product')
        brand_name = data.get('brand_name', '')
        color = data.get('color', '')
        logo_url = data.get('logo_url', '')
        image_b64 = data.get('image_b64')
        chat_id = data.get('chat_id')
        
        if not image_b64 or not product:
            return jsonify({"error": "Missing required data"}), 400
        
        # Save image to disk
        GENERATED_DIR = os.path.join("static", "generated")
        os.makedirs(GENERATED_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"mockup_{product}_{timestamp}_{uuid.uuid4().hex[:6]}.png"
        file_path = os.path.join(GENERATED_DIR, filename)
        
        # Decode and save
        img_bytes = base64.b64decode(image_b64)
        with open(file_path, "wb") as f:
            f.write(img_bytes)
        
        # Use same file for thumbnail for now
        thumb_path = file_path 
        
        # Save to database
        mockup_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO mockup_history 
            (id, user_id, product, brand_name, color, logo_path, generated_image_path, thumbnail_path, chat_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (mockup_id, user_id, product, brand_name, color, logo_url, file_path, thumb_path, chat_id))
        conn.commit()
        conn.close()
        
        print(f"✅ Mockup saved to library: {filename}")
        
        return jsonify({
            "status": "ok",
            "mockup_id": mockup_id,
            "file_path": file_path
        })
        
    except Exception as e:
        print(f"❌ Save to library error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/get-library', methods=['GET'])
def get_library():
    """✅ Return all generated mockups for photo library"""
    user_id = request.headers.get('X-User-ID', 'guest')
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            id, product, brand_name, color, logo_path, generated_image_path,
            thumbnail_path, created_at, chat_id
        FROM mockup_history
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    
    mockups = []
    for row in cursor.fetchall():
        (mockup_id, product, brand_name, color, logo_path,
         generated_image_path, thumbnail_path, created_at, chat_id) = row
        
        # Convert file paths to URLs relative to static
        # Assuming path stored is like "static/generated/file.png"
        gen_url = generated_image_path
        if generated_image_path and not generated_image_path.startswith('http'):
             # Fix for windows/linux path separators if necessary
             clean_path = generated_image_path.replace('\\', '/')
             gen_url = clean_path

        thumb_url = gen_url
        
        mockups.append({
            "id": mockup_id,
            "product": product,
            "brand_name": brand_name,
            "color": color,
            "logo_path": logo_path,
            "generated_image": gen_url,
            "thumbnail_url": thumb_url,
            "created_at": created_at,
            "chat_id": chat_id
        })
    
    conn.close()
    
    return jsonify({
        "status": "ok",
        "mockups": mockups
    })

from flask import send_file
import base64
from io import BytesIO

from flask import send_file, jsonify, request
import base64
from io import BytesIO

# =========================================================================
# 🔐 PROXY GOOGLE APPS SCRIPT (SAME LOGIC, MORE SECURE)
# =========================================================================

GAS_URL = os.environ.get("GAS_URL")

@app.route("/save_user_data", methods=["POST"])
def save_user_data():
    try:
        data = request.json

        response = requests.post(
            GAS_URL,
            data=data,  # IMPORTANT: same as URLSearchParams
            timeout=10
        )

        return jsonify({"success": True})

    except Exception as e:
        print("❌ GAS error:", e)
        return jsonify({"success": False}), 500
    

#email verification function


from flask_mail import Mail, Message
import threading

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')  # Add to .env file
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASSWORD')  # Add to .env file
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('EMAIL_USER')

mail = Mail(app)
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
@app.route('/generate_vm_sheet_enhanced', methods=['POST'])
def generate_vm_sheet_enhanced():
    """✅ Generate VM Sheet with Phone Verification + Email Welcome"""
    
    try:
        data = request.json
        
        selected_products = data.get('products', [])
        logo_b64 = data.get('logo_b64')
        brand_name = data.get('brand_name', 'Greenwich Packaging')
        color = data.get('color', '#FFFFFF')
        logo_mime_type = data.get('logo_mime_type', 'image/png')
        
        # ✅ NEW: Get verification details
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        
        print(f"\n🎨 VM Sheet Request:")
        print(f"  Products: {len(selected_products)}")
        print(f"  Brand: {brand_name}")
        print(f"  Color: {color}")
        print(f"  Email: {email}")
        print(f"  Phone: {phone}")
        
        # ✅ Validation
        if not selected_products or not logo_b64:
            return jsonify({"error": "Missing products or logo"}), 400
        
        if not validate_email(email):
            return jsonify({"error": "Invalid email address"}), 400
        
        if not validate_international_phone(phone):
            return jsonify({"error": "Invalid phone number"}), 400
        
        # Clean logo
        if ',' in logo_b64:
            logo_b64 = logo_b64.split(',')[1]
        
        # Generate mockups for each product
        generated_images = []
        
        for product_id in selected_products:
            product_path = PRODUCT_MAP.get(product_id)
            if not product_path:
                continue
            
            full_path = os.path.join(app.root_path, product_path)
            if not os.path.exists(full_path):
                continue
            
            try:
                # Load product image
                with open(full_path, 'rb') as f:
                    product_data = f.read()
                product_b64 = base64.b64encode(product_data).decode("utf-8")
                
                # ✅ USE PRODUCT-SPECIFIC PROMPT
                base_prompt = PRODUCT_PROMPTS.get(product_id, 
                    "Generate professional packaging mockup with uploaded logo.")
                
                # Inject color
                if color and color.lower() != 'none':
                    color_rule = f"Use {color} as primary packaging color."
                else:
                    color_rule = "Keep original color."
                
                prompt = base_prompt.replace('{COLOR_RULE}', color_rule)
                
                if brand_name != 'Greenwich Packaging':
                    prompt += f" Include brand name '{brand_name}' elegantly."
                
                # API call
                parts_list = [
                    {"text": prompt},
                    {"inlineData": {"mimeType": "image/jpeg", "data": product_b64}},
                    {"inlineData": {"mimeType": logo_mime_type, "data": logo_b64}}
                ]
                
                payload = {
                    "contents": [{"parts": parts_list}],
                    "generationConfig": {"responseModalities": ["IMAGE"]}
                }
                
                response = requests.post(
                    GEMINI_IMAGE_API_URL,
                    json=payload,
                    headers={"Content-Type": "application/json"},
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
                            "product_name": product_id.replace('_', ' ').title(),
                            "image_data": img_data
                        })
                        
                        print(f"  ✅ Generated: {product_id}")
                    
            except Exception as e:
                print(f"  ❌ Error on {product_id}: {e}")
                continue
        
        if not generated_images:
            return jsonify({"error": "No mockups generated"}), 500
        
        # ✅ CREATE PDF WITH GREENWICH BRANDING
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.colors import HexColor
        
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=A4)
        width, height = A4
        
        # Colors
        green = HexColor('#00B050')
        white = HexColor('#FFFFFF')
        black = HexColor('#1A1A1A')
        
        # ====================================================================
        # ✅ COVER PAGE
        # ====================================================================
        c.setFillColor(white)
        c.rect(0, 0, width, height, fill=True, stroke=False)
        
        # Top Green Bar
        c.setFillColor(green)
        c.rect(0, height - 100, width, 100, fill=True, stroke=False)
        
        # Greenwich Logo
        try:
            greenwich_logo_path = os.path.join(app.root_path, 'static', 'gp-logo.png')
            if os.path.exists(greenwich_logo_path):
                c.drawImage(greenwich_logo_path, 
                           (width - 180) / 2, height / 2 + 80,
                           width=180, height=180,
                           preserveAspectRatio=True, mask='auto')
        except:
            pass
        
        # Main Title
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 48)
        c.drawCentredString(width/2, height / 2 - 20, "BRANDING")
        c.drawCentredString(width/2, height / 2 - 70, "GUIDELINES")
        
        # Brand Name
        c.setFont("Helvetica", 18)
        c.drawCentredString(width/2, height / 2 - 120, brand_name.upper())
        
        # Footer
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, 80, f"{len(generated_images)} Products")
        c.drawCentredString(width/2, 60, datetime.now().strftime('%d %B %Y'))
        
        c.showPage()
        
        # ====================================================================
        # ✅ PRODUCT PAGES
        # ====================================================================
        for idx, mockup in enumerate(generated_images):
            c.setFillColor(white)
            c.rect(0, 0, width, height, fill=True, stroke=False)
            
            # Header
            c.setFillColor(green)
            c.rect(0, height - 50, width, 50, fill=True, stroke=False)
            
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 20)
            c.drawCentredString(width/2, height - 28, mockup['product_name'].upper())
            
            # Product Image
            try:
                img = Image.open(io.BytesIO(mockup['image_data']))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                
                c.drawImage(ImageReader(img_buffer), 
                           50, 100,
                           width=width - 100, height=height - 200,
                           preserveAspectRatio=True, mask='auto')
            except:
                pass
            
            # Footer
            c.setFont("Helvetica", 9)
            c.drawCentredString(width/2, 30, f"Page {idx + 2} | Greenwich Packaging")
            
            c.showPage()
        
        c.save()
        pdf_buffer.seek(0)
        
        print(f"✅ PDF Created: {len(generated_images) + 1} pages")
        
        # ✅ Send Welcome Email (in background)
        send_welcome_email(email, brand_name)
        
        print(f"✅ VM Sheet generated for {email}\n")
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Greenwich_VM_Sheet_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        print(f"❌ VM Sheet Error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
# =========================================================================
# ✅ MAIN ENTRY POINT (UNCHANGED)
# =========================================================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 AI PACKAGING DESIGNER - Backend Server Starting...")
    print("="*70)
    print(f"✅ Gemini API Key: {'Configured' if API_KEY else '❌ Missing'}")
    print(f"✅ Chat Client: {'Initialized' if chat_client else '❌ Failed'}")
   
    print("="*70 + "\n")
    
    app.run(host="0.0.0.0", port=8080, debug=True)

    # =========================================================================
# 🔒 FINAL PRODUCT AUTHORITY FIX (PASTE AT END OF app.py)
# =========================================================================

def ENFORCE_SELECTED_PRODUCT_ONLY(user_prompt, selected_product):
    """
    FINAL AUTHORITY RULE:
    - UI selected product ALWAYS wins
    - User text product is IGNORED
    - If selected product is invalid → STOP
    """

    if not selected_product or selected_product not in PRODUCT_MAP:
        return jsonify({
            "error": True,
            "message": "❌ Please select a valid product before generating."
        }), 400

    # 🔥 HARD OVERRIDE PROMPT
    safe_prompt = (
        f"You are generating a packaging design ONLY for: {selected_product.replace('_',' ')}.\n"
        f"IGNORE any other product mentioned by the user.\n\n"
        f"User design instructions (style only): {user_prompt}"
    )

    return safe_prompt, selected_product

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


