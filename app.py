from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify, send_file
import os
from datetime import datetime, timedelta
import uuid
import random
from werkzeug.security import check_password_hash, generate_password_hash
from json_encoder import CustomJSONEncoder
from pymongo import MongoClient
from bson.objectid import ObjectId
from pymongo.server_api import ServerApi

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'gogoprint_secret_key_dev')
app.json_encoder = CustomJSONEncoder

# MongoDB Connection
client = MongoClient("mongodb+srv://test:1zrbAbwhLkw360dq@gogoprint.z5cf4yu.mongodb.net/?retryWrites=true&w=majority&appName=GoGoPrint", server_api=ServerApi('1'))
db = client.gogoprint_db  # Database name

# Initialize admin user if not exists
if db.users.count_documents({'email': 'admin@gogoprint.com'}) == 0:
    admin_user = {
        'name': 'Admin User',
        'email': 'admin@gogoprint.com',
        'password': generate_password_hash('admin123'),
        'created_at': datetime.now()
    }
    db.users.insert_one(admin_user)
    print("Created admin user: admin@gogoprint.com / admin123")

# Predefined chat data with image filenames
chats_data = [
    {
        'id': '1',
        'title': "Cable chaos turned classy",
        'user_message': "Can you help me design a desktop cable management system that hides USB hubs, has clips for routing, and fits behind a dual-monitor stand?",
        'bot_response': "I've created a 3D model that emphasizes hidden compartments and snap-fit assembly. It should neatly tuck under most desk edges and includes cable clips optimized for standard 5mm cables.",
        'model_name': "desktop_cable_management.stl",
        'image_filename': "desktop_cable_management.png",
        'timestamp': datetime.now() - timedelta(days=4)
    },
    {
        'id': '2',
        'title': "Light it up with angles",
        'user_message': "I'm looking for a geometric lampshade that gives cool shadows and works with standard IKEA sockets.",
        'bot_response': "Here's your 3D model! The geometric patterns maximize light diffusion while keeping structural integrity. It prints without supports and has a twist-lock base compatible with most E26 sockets.",
        'model_name': "geometric_lampshade.stl",
        'image_filename': "geometric_lampshade.png",
        'timestamp': datetime.now() - timedelta(days=3)
    },
    {
        'id': '3',
        'title': "Desk Tetris 3000",
        'user_message': "I want a modular desk organizer that lets me stack and rearrange compartments for pens, sticky notes, and USBs.",
        'bot_response': "Your modular system features interlocking connections and a minimalist design. Each tray nests snugly, and optional hooks allow it to hang off shelves too!",
        'model_name': "modular_desk_organizer.stl",
        'image_filename': "modular_desk_organizer.png",
        'timestamp': datetime.now() - timedelta(days=2)
    },
    {
        'id': '4',
        'title': "Lazy stand, active grip",
        'user_message': "Can you design a phone holder I can use at the gym treadmill? Needs to tilt, grip tight, and have cable pass-through.",
        'bot_response': "This stand features an ergonomic grip and ventilation slots for sweaty sessions. I added a hidden compartment for earbuds and a channel to hold your charger in place.",
        'model_name': "phone_holder.stl",
        'image_filename': "phone_holder.png",
        'timestamp': datetime.now() - timedelta(days=1)
    }
]

# Create structured chat and message data
def get_chat_data(chat_id=None):
    if chat_id:
        # Return specific chat
        for chat in chats_data:
            if chat['id'] == chat_id:
                return chat
        return None
    else:
        # Return all chats
        return chats_data

def get_chat_messages(chat_id):
    chat = get_chat_data(chat_id)
    if not chat:
        return []
    
    # Base timestamp for message ordering
    base_timestamp = chat['timestamp']
    
    # Create message history
    messages = [
        {
            'sender': 'user',
            'content': chat['user_message'],
            'timestamp': base_timestamp
        },
        {
            'sender': 'bot',
            'content': chat['bot_response'],
            'model_preview': True,
            'model_name': chat['model_name'],
            'model_size': f"{random.randint(1, 5)}.{random.randint(1,9)} MB",
            'timestamp': base_timestamp + timedelta(minutes=1)
        }
    ]
    
    # Add print settings conversation based on model type
    if "Cable chaos" in chat['title']:
        settings_response = """Here are the recommended print settings for your Cable Management System:

Layer Height: 0.2mm
Infill: 15% cubic
Material: PLA
Nozzle Temperature: 200-210°C
Bed Temperature: 60°C
Print Speed: 50mm/s
Wall Thickness: 1.2mm
Supports: None required
Cooling: 100% after first layer"""
    
    elif "Light it up" in chat['title']:
        settings_response = """Here are the recommended print settings for your Geometric Lampshade:

Layer Height: 0.16mm (for fine details)
Infill: 10% gyroid (for interesting shadow patterns)
Material: Translucent PETG or PLA
Nozzle Temperature: 215-225°C
Bed Temperature: 60-70°C
Print Speed: 40mm/s
Wall Thickness: 0.8mm (thin walls for better light diffusion)
Supports: Only for overhangs >60°
Cooling: 100% after layer 3"""
    
    elif "Desk Tetris" in chat['title']:
        settings_response = """Here are the recommended print settings for your Modular Desk Organizer:

Layer Height: 0.2mm
Infill: 20% cubic
Material: PLA or PETG for durability
Nozzle Temperature: 205-220°C
Bed Temperature: 60-65°C
Print Speed: 50-60mm/s
Wall Thickness: 1.6mm (for durability)
Supports: None needed
First Layer: 0.3mm height at 30mm/s for better adhesion
Cooling: 100% after first layer"""
    
    elif "Lazy stand" in chat['title']:
        settings_response = """Here are the recommended print settings for your Phone Holder:

Layer Height: 0.16mm
Infill: 25% for strength
Material: PETG for flexibility and durability
Nozzle Temperature: 230-240°C
Bed Temperature: 70-80°C
Print Speed: 45mm/s
Wall Thickness: 1.6mm (4 perimeters with 0.4mm nozzle)
Retraction: 6mm at 45mm/s to prevent stringing
Supports: Only where needed for overhangs
Cooling: 80% to ensure good layer adhesion"""
    
    else:
        settings_response = """Here are the recommended general print settings:

Layer Height: 0.2mm (0.16mm for fine details)
Infill: 20% cubic or gyroid
Material: PLA (PETG for functional parts)
Nozzle Temperature: 200-210°C for PLA, 230-240°C for PETG
Bed Temperature: 60°C for PLA, 70-80°C for PETG
Print Speed: 50mm/s
Wall Thickness: 1.2mm (3 perimeters with 0.4mm nozzle)
Supports: Only where needed
Cooling: 100% after first layer"""
    
    # Add user question about print settings (2 minutes after initial response)
    messages.append({
        'sender': 'user',
        'content': "What are the recommended print settings for this model?",
        'timestamp': base_timestamp + timedelta(minutes=3)
    })
    
    # Add bot response with print settings (1 minute after the question)
    messages.append({
        'sender': 'bot',
        'content': settings_response,
        'timestamp': base_timestamp + timedelta(minutes=4)
    })
    
    return messages

# Add this new route for the home page
@app.route('/home')
def home():
    return render_template('home.html')

# Modify the existing index route
@app.route('/')
def index():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('home'))
    
    # User is logged in, show chat interface
    user_name = session.get('user_name', 'Demo User')
    user_email = session.get('user_email', 'demo@example.com')
    
    # Get all predefined chats
    recent_chats = get_chat_data()
    
    # Convert to format expected by the template
    for chat in recent_chats:
        chat['_id'] = chat['id']
        chat['image'] = chat['image_filename']
    
    return render_template('index.html', 
                          user_name=user_name,
                          user_email=user_email,
                          recent_chats=recent_chats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Find the user in the database
        user = db.users.find_one({'email': email})
        
        if user and check_password_hash(user['password'], password):
            # Set session variables
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Basic validation
        if not all([name, email, password, confirm_password]):
            flash('All fields are required', 'error')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
            
        # Check if user already exists
        existing_user = db.users.find_one({'email': email})
        if existing_user:
            flash('Email already registered', 'error')
            return render_template('register.html')
            
        # Create new user
        hashed_password = generate_password_hash(password)
        user = {
            'name': name,
            'email': email,
            'password': hashed_password,
            'created_at': datetime.now()
        }
        
        user_id = db.users.insert_one(user).inserted_id
        
        # Log in the user
        session['user_id'] = str(user_id)
        session['user_name'] = name
        session['user_email'] = email
        
        flash('Registration successful!', 'success')
        return redirect(url_for('index'))
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    # Clear any session data
    session.clear()
    # Redirect to home page
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('home'))

@app.route('/chat/<chat_id>')
def view_chat(chat_id):
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_name = session.get('user_name', 'Demo User')
    user_email = session.get('user_email', 'demo@example.com')
    
    # Get the specific chat
    chat = get_chat_data(chat_id)
    if not chat:
        flash('Chat not found', 'error')
        return redirect(url_for('index'))
    
    # Format for template
    chat_data = {
        '_id': chat['id'],
        'title': chat['title'],
        'image': chat['image_filename']
    }
    
    # Get messages for this chat
    messages = get_chat_messages(chat_id)
    
    # Get all chats for the sidebar
    recent_chats = get_chat_data()
    for recent_chat in recent_chats:
        recent_chat['_id'] = recent_chat['id']
        recent_chat['image'] = recent_chat['image_filename']
    
    return render_template('chat.html',
                        chat=chat_data,
                        messages=messages,
                        user_name=user_name,
                        user_email=user_email,
                        recent_chats=recent_chats)

@app.route('/chat/send', methods=['POST'])
def send_chat_message():
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in', 'success': False}), 401
    
    data = request.get_json()
    chat_id = data.get('chat_id')
    message = data.get('message')
    
    if not chat_id or not message:
        return jsonify({'error': 'Missing required fields', 'success': False}), 400
    
    try:
        # Check if the message is asking about print settings
        if any(keyword in message.lower() for keyword in ['printer settings', 'print settings', 'how to print', 'settings']):
            # Get the specific chat
            chat = get_chat_data(chat_id)
            if not chat:
                return jsonify({'error': 'Chat not found', 'success': False}), 404
                
            # Determine which model and provide specific settings
            model_type = chat['title']
            
            # Create organized settings response based on the model
            if "Cable chaos" in model_type:
                settings_response = """Here are the recommended print settings for your Cable Management System:

Layer Height: 0.2mm
Infill: 15% cubic
Material: PLA
Nozzle Temperature: 200-210°C
Bed Temperature: 60°C
Print Speed: 50mm/s
Wall Thickness: 1.2mm
Supports: None required
Cooling: 100% after first layer"""
            
            elif "Light it up" in model_type:
                settings_response = """Here are the recommended print settings for your Geometric Lampshade:

Layer Height: 0.16mm (for fine details)
Infill: 10% gyroid (for interesting shadow patterns)
Material: Translucent PETG or PLA
Nozzle Temperature: 215-225°C
Bed Temperature: 60-70°C
Print Speed: 40mm/s
Wall Thickness: 0.8mm (thin walls for better light diffusion)
Supports: Only for overhangs >60°
Cooling: 100% after layer 3"""
            
            elif "Desk Tetris" in model_type:
                settings_response = """Here are the recommended print settings for your Modular Desk Organizer:

Layer Height: 0.2mm
Infill: 20% cubic
Material: PLA or PETG for durability
Nozzle Temperature: 205-220°C
Bed Temperature: 60-65°C
Print Speed: 50-60mm/s
Wall Thickness: 1.6mm (for durability)
Supports: None needed
First Layer: 0.3mm height at 30mm/s for better adhesion
Cooling: 100% after first layer"""
            
            elif "Lazy stand" in model_type:
                settings_response = """Here are the recommended print settings for your Phone Holder:

Layer Height: 0.16mm
Infill: 25% for strength
Material: PETG for flexibility and durability
Nozzle Temperature: 230-240°C
Bed Temperature: 70-80°C
Print Speed: 45mm/s
Wall Thickness: 1.6mm (4 perimeters with 0.4mm nozzle)
Retraction: 6mm at 45mm/s to prevent stringing
Supports: Only where needed for overhangs
Cooling: 80% to ensure good layer adhesion"""
            
            else:
                settings_response = """Here are the recommended general print settings:

Layer Height: 0.2mm (0.16mm for fine details)
Infill: 20% cubic or gyroid
Material: PLA (PETG for functional parts)
Nozzle Temperature: 200-210°C for PLA, 230-240°C for PETG
Bed Temperature: 60°C for PLA, 70-80°C for PETG
Print Speed: 50mm/s
Wall Thickness: 1.2mm (3 perimeters with 0.4mm nozzle)
Supports: Only where needed
Cooling: 100% after first layer"""
                
            bot_response_id = str(uuid.uuid4())
            bot_response = {
                '_id': bot_response_id,
                'content': settings_response,
                'sender': 'bot',
                'timestamp': datetime.now()
            }
        else:
            # Generic response for any other message
            bot_response_id = str(uuid.uuid4())
            bot_response = {
                '_id': bot_response_id,
                'content': f"I've analyzed your request for: {message}. I can help you design a 3D model that meets your specifications. Would you like me to focus on functionality or aesthetics?",
                'sender': 'bot',
                'timestamp': datetime.now()
            }
        
        return jsonify({
            'success': True,
            'user_message': {
                'content': message,
                'sender': 'user',
                'timestamp': datetime.now()
            },
            'bot_response': bot_response,
            'bot_response_id': bot_response_id,
            'loading': False
        })
    except Exception as e:
        print(f"Exception in send_chat_message: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/new_chat', methods=['POST'])
def new_chat():
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    try:
        # Simulate creating a new chat - just return the ID of the first chat
        # In a real app, you would create a new chat in the database
        return jsonify({
            'success': True,
            'chat_id': '1'  # Return the first chat ID
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/generate_image', methods=['POST'])
def generate_image():
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in', 'success': False}), 401
    
    data = request.get_json()
    chat_id = data.get('chat_id')
    message = data.get('message')
    bot_response_id = data.get('bot_response_id')
    
    if not chat_id or not message or not bot_response_id:
        return jsonify({'error': 'Missing required fields', 'success': False}), 400
    
    try:
        # Instead of generating, use one of our predefined images
        image_options = ["desktop_cable_management.png", "geometric_lampshade.png", 
                        "modular_desk_organizer.png", "phone_holder.png", "white_logo.png"]
        
        image_filename = random.choice(image_options)
        
        # Create a response with the selected image
        bot_response = {
            '_id': bot_response_id,
            'content': "Here's your 3D model based on your specifications!",
            'model_preview': True,
            'model_name': image_filename,
            'model_size': f"{random.randint(1, 5)}.{random.randint(1,9)} MB",
            'sender': 'bot',
            'timestamp': datetime.now(),
            'is_loading': False
        }
        
        return jsonify({
            'success': True,
            'bot_response': bot_response,
            'loading': False
        })
    except Exception as e:
        print(f"Exception in generate_image route: {str(e)}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/download/<filename>')
def download_file(filename):
    # Check if user is logged in
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    try:
        # Convert any file extension to .png
        base_filename = os.path.splitext(filename)[0]
        png_filename = f"{base_filename}.png"
        
        # Look for the PNG file in the img directory
        file_path = os.path.join('static', 'img', png_filename)
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=png_filename
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/test')
def test():
    return jsonify({'status': 'ok', 'message': 'Server is running'})

if __name__ == '__main__':
    # Create indexes for better performance
    db.users.create_index('email', unique=True)
    app.run(debug=True, port=5001)