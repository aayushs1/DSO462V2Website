from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
import os
from datetime import datetime, timedelta
import uuid
import random
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash
from pymongo.server_api import ServerApi

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'gogoprint_secret_key_dev')

# MongoDB Connection
client = MongoClient("mongodb+srv://test:1zrbAbwhLkw360dq@gogoprint.z5cf4yu.mongodb.net/?retryWrites=true&w=majority&appName=GoGoPrint", server_api=ServerApi('1'))
db = client.gogoprint_db  # Database name

# Manual curated chat data with image filenames
def make_chat(chat_id, title, user_message, bot_response, model_name, image_filename):
    now = datetime.now()
    
    # Create chat document
    chat = {
        'title': title,
        'user_id': 'philbert_loekman',  # Default user for testing
        'created_at': now,
        'last_updated': now + timedelta(minutes=2),
        'image': image_filename
    }
    
    # Insert chat and get MongoDB _id
    chat_object_id = db.chats.insert_one(chat).inserted_id
    
    # Create messages
    messages = [
        {
            'chat_id': chat_object_id,
            'sender': 'user',
            'content': user_message,
            'timestamp': now
        },
        {
            'chat_id': chat_object_id,
            'sender': 'bot',
            'content': bot_response,
            'model_preview': True,
            'model_name': model_name,
            'model_size': f"{random.randint(1, 5)}.{random.randint(1,9)} MB",
            'timestamp': now + timedelta(minutes=1)
        }
    ]
    
    # Insert messages
    db.messages.insert_many(messages)
    
    return {
        'chat_id': chat_object_id,
        'title': title
    }

chats_data = [
    {
        'title': "Cable chaos turned classy",
        'user_message': "Can you help me design a desktop cable management system that hides USB hubs, has clips for routing, and fits behind a dual-monitor stand?",
        'bot_response': "I've created a 3D model that emphasizes hidden compartments and snap-fit assembly. It should neatly tuck under most desk edges and includes cable clips optimized for standard 5mm cables.",
        'model_name': "desktop_cable_management.stl",
        'image_filename': "desktop_cable_management.png"
    },
    {
        'title': "Light it up with angles",
        'user_message': "I'm looking for a geometric lampshade that gives cool shadows and works with standard IKEA sockets.",
        'bot_response': "Here's your 3D model! The geometric patterns maximize light diffusion while keeping structural integrity. It prints without supports and has a twist-lock base compatible with most E26 sockets.",
        'model_name': "geometric_lampshade.stl",
        'image_filename': "geometric_lampshade.png"
    },
    {
        'title': "Desk Tetris 3000",
        'user_message': "I want a modular desk organizer that lets me stack and rearrange compartments for pens, sticky notes, and USBs.",
        'bot_response': "Your modular system features interlocking connections and a minimalist design. Each tray nests snugly, and optional hooks allow it to hang off shelves too!",
        'model_name': "modular_desk_organizer.stl",
        'image_filename': "modular_desk_organizer.png"
    },
    {
        'title': "Lazy stand, active grip",
        'user_message': "Can you design a phone holder I can use at the gym treadmill? Needs to tilt, grip tight, and have cable pass-through.",
        'bot_response': "This stand features an ergonomic grip and ventilation slots for sweaty sessions. I added a hidden compartment for earbuds and a channel to hold your charger in place.",
        'model_name': "phone_holder.stl",
        'image_filename': "phone_holder.png"
    }
]

def load_curated_chat_data():
    # Check if data already exists to avoid duplicates
    if db.chats.count_documents({}) == 0:
        for chat_info in chats_data:
            make_chat(
                str(uuid.uuid4()),
                chat_info['title'],
                chat_info['user_message'],
                chat_info['bot_response'],
                chat_info['model_name'],
                chat_info['image_filename']
            )

@app.route('/')
def index():
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get user information
    user_id = session['user_id']
    user_name = session.get('user_name', 'User')
    user_email = session.get('user_email', '')
    
    # Get only the chats belonging to this user
    recent_chats = list(db.chats.find({'user_id': user_id}).sort('last_updated', -1).limit(10))
    
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

@app.route('/logout')
def logout():
    # Clear all session data
    session.clear()
    # Redirect to login page or home page
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/chat/<chat_id>')
def view_chat(chat_id):
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_name = session.get('user_name', 'User')
    user_email = session.get('user_email', '')
    
    try:
        # Convert string chat_id to ObjectId
        chat_object_id = ObjectId(chat_id)
        
        # Get the chat and verify it belongs to this user
        chat = db.chats.find_one({'_id': chat_object_id, 'user_id': user_id})
        if not chat:
            flash('Chat not found or you do not have permission to view it', 'error')
            return redirect(url_for('index'))
        
        # Get the messages for this chat
        messages = list(db.messages.find({'chat_id': chat_object_id}).sort('timestamp', 1))
        
        # Get recent chats for the sidebar
        recent_chats = list(db.chats.find({'user_id': user_id}).sort('last_updated', -1).limit(10))
        
        return render_template('chat.html',
                            chat=chat,
                            messages=messages,
                            user_name=user_name,
                            user_email=user_email,
                            recent_chats=recent_chats)
    except Exception as e:
        flash(f'Error loading chat: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/new_chat', methods=['POST'])
def new_chat():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    
    user_id = session['user_id']
    title = request.json.get('title', 'New Chat')
    
    # Create a new chat document with user_id
    chat = {
        'title': title,
        'user_id': user_id,
        'created_at': datetime.now(),
        'last_updated': datetime.now(),
        'image': 'default_chat.png'  # Default image or whatever you use
    }
    
    chat_id = db.chats.insert_one(chat).inserted_id
    
    return jsonify({'success': True, 'chat_id': str(chat_id)})

@app.route('/message/send', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401
        
    data = request.json
    chat_id = data.get('chat_id')
    message_text = data.get('message')
    
    if not chat_id or not message_text:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        chat_object_id = ObjectId(chat_id)
        now = datetime.now()
        
        # Get the chat to check if it belongs to the user
        chat = db.chats.find_one({'_id': chat_object_id, 'user_id': session['user_id']})
        if not chat:
            return jsonify({'error': 'Chat not found or access denied'}), 403
        
        # If this is a new chat with default title, update the title based on first message
        if chat['title'] == 'New Chat':
            title = ' '.join(message_text.split()[:5])
            title = (title[:27] + '...') if len(title) > 30 else title
            db.chats.update_one(
                {'_id': chat_object_id},
                {'$set': {'title': title, 'last_updated': now}}
            )
        else:
            # Just update the last_updated timestamp
            db.chats.update_one(
                {'_id': chat_object_id},
                {'$set': {'last_updated': now}}
            )

        # Insert user message
        user_message_id = str(uuid.uuid4())
        user_message = {
            'message_id': user_message_id,  # Custom ID for references
            'chat_id': chat_object_id,
            'sender': 'user',
            'content': message_text,
            'timestamp': now
        }
        db.messages.insert_one(user_message)

        # Generate bot response (mock implementation)
        bot_response_time = now + timedelta(seconds=2)
        bot_message_id = str(uuid.uuid4())
        bot_response = {
            'message_id': bot_message_id,  # Custom ID for references
            'chat_id': chat_object_id,
            'sender': 'bot',
            'content': f"Here's a quick draft based on your message: {message_text}",
            'model_preview': True,
            'model_name': f"generated_model_{chat_id[:6]}.stl",
            'model_size': f"{random.randint(1, 5)}.{random.randint(1, 9)} MB",
            'timestamp': bot_response_time
        }
        db.messages.insert_one(bot_response)
        
        # Update chat last_updated time
        db.chats.update_one(
            {'_id': chat_object_id},
            {'$set': {'last_updated': bot_response_time}}
        )

        # Convert timestamps to string for JSON serialization
        bot_response_json = bot_response.copy()
        bot_response_json['timestamp'] = bot_response_json['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        bot_response_json['chat_id'] = str(bot_response_json['chat_id'])  # Convert ObjectId to string

        return jsonify({
            'user_message_id': user_message_id,
            'bot_message_id': bot_message_id,
            'bot_response': bot_response_json
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/load-curated-chats')
def load_curated_chats():
    load_curated_chat_data()
    chat_count = db.chats.count_documents({})
    return jsonify({
        'status': 'Loaded curated chat dataset',
        'chat_count': chat_count
    })

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

if __name__ == '__main__':
    # Create indexes for better performance
    db.chats.create_index([('user_id', 1), ('last_updated', -1)])
    db.messages.create_index([('chat_id', 1), ('timestamp', 1)])
    db.users.create_index('email', unique=True)
    
    # Load sample data
    load_curated_chat_data()
    
    # Check if admin user exists, create if not
    if db.users.count_documents({'email': 'admin@gogoprint.com'}) == 0:
        admin_user = {
            'name': 'Admin User',
            'email': 'admin@gogoprint.com',
            'password': generate_password_hash('admin123'),
            'created_at': datetime.now()
        }
        db.users.insert_one(admin_user)
        print("Created admin user: admin@gogoprint.com / admin123")
    
    app.run(debug=True)