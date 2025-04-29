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
import markdown
import bleach

# Define allowed HTML tags and attributes for Markdown conversion
ALLOWED_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'a', 'ul', 'ol', 
                'li', 'strong', 'em', 'blockquote', 'code', 'pre', 'hr', 'img']
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
}

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'gogoprint_secret_key_dev')
app.json_encoder = CustomJSONEncoder

# Add escapejs filter
@app.template_filter('escapejs')
def escapejs_filter(value):
    """Escape a string for use in JavaScript."""
    if value is None:
        return ''
    value = str(value)
    value = value.replace('\\', '\\\\')
    value = value.replace('"', '\\"')
    value = value.replace("'", "\\'")
    value = value.replace('\n', '\\n')
    value = value.replace('\r', '\\r')
    value = value.replace('\t', '\\t')
    return value

# Add context processor to make user information available to all templates
@app.context_processor
def inject_user():
    if 'user_id' in session:
        return {
            'user_name': session.get('user_name', ''),
            'user_email': session.get('user_email', '')
        }
    return {
        'user_name': '',
        'user_email': ''
    }

# MongoDB Connection
client = MongoClient(app.secret_key, server_api=ServerApi('1'))
db = client.gogoprint_db  # Database name

# Initialize admin user if not exists
if db.users.count_documents({'email': 'admin@gogoprint.net'}) == 0:
    admin_user = {
        'name': 'Admin User',
        'email': 'admin@gogoprint.net',
        'password': generate_password_hash('admin123'),
        'created_at': datetime.now()
    }
    db.users.insert_one(admin_user)
    print("Created admin user: admin@gogoprint.net / admin123")

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

# Modify the existing index route to be dashboard
@app.route('/dashboard')
def dashboard():
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
    
    return render_template('dashboard.html', 
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
            
            return redirect(url_for('dashboard'))
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
        return redirect(url_for('dashboard'))
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    # Clear any session data
    session.clear()
    # Redirect to home page
    return redirect(url_for('home'))

@app.route('/dashboard/<chat_id>')
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
        return redirect(url_for('dashboard'))
    
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

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    print("Contact route accessed")  # Debug logging
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        print(f"Contact form submitted: {name}, {email}")  # Debug logging
        # Process the form data here
        flash('Thank you for your message! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

# Blog related routes
@app.route('/blog')
def blog_list():
    print("Blog list route accessed")  # Debug logging
    category = request.args.get('category')
    search_query = request.args.get('search', '').strip()
    
    # Build the query based on category and search
    query = {}
    if category and category != 'All':
        query['category'] = category
    
    if search_query:
        # Search in title and content
        query['$or'] = [
            {'title': {'$regex': search_query, '$options': 'i'}},
            {'content': {'$regex': search_query, '$options': 'i'}}
        ]
    
    # Retrieve blog posts, sorted by creation date (newest first)
    posts = list(db.blog_posts.find(query).sort('created_at', -1))
    print(f"Found {len(posts)} blog posts")  # Debug logging
    
    # Format datetime for display
    for post in posts:
        post['formatted_date'] = post['created_at'].strftime('%B %d, %Y')
        # Get the author name
        if 'author_id' in post:
            author = db.users.find_one({'_id': ObjectId(post['author_id'])})
            post['author_name'] = author['name'] if author else 'Unknown Author'
        else:
            post['author_name'] = 'Unknown Author'
        
        # Create a short preview (first 200 characters)
        post['preview'] = post['content'][:200] + '...' if len(post['content']) > 200 else post['content']
    
    return render_template('blog_list.html', posts=posts, current_category=category, search_query=search_query)

@app.route('/blog/<post_id>')
def blog_detail(post_id):
    # Retrieve the specific blog post
    post = db.blog_posts.find_one({'_id': ObjectId(post_id)})
    
    if not post:
        flash('Blog post not found', 'error')
        return redirect(url_for('blog_list'))
    
    # Format datetime for display
    post['formatted_date'] = post['created_at'].strftime('%B %d, %Y')
    
    # Get author information
    if 'author_id' in post:
        author = db.users.find_one({'_id': ObjectId(post['author_id'])})
        post['author_name'] = author['name'] if author else 'Unknown Author'
    else:
        post['author_name'] = 'Unknown Author'
    
    # Convert markdown content to HTML if the content is in markdown format
    if post.get('content_format') == 'markdown':
        # Convert markdown to HTML and sanitize it
        html_content = markdown.markdown(post['content'])
        post['html_content'] = bleach.clean(html_content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
    else:
        # For plain text, just replace newlines with <br> tags
        post['html_content'] = post['content'].replace('\n', '<br>')
    
    # Get related posts (same category)
    if 'category' in post:
        related_posts = list(db.blog_posts.find(
            {'category': post['category'], '_id': {'$ne': ObjectId(post_id)}}
        ).sort('created_at', -1).limit(3))
        
        for related in related_posts:
            related['formatted_date'] = related['created_at'].strftime('%B %d, %Y')
    else:
        related_posts = []
    
    return render_template('blog_detail.html', post=post, related_posts=related_posts)

@app.route('/blog/new', methods=['GET', 'POST'])
def blog_new():
    # Check if user is logged in
    if 'user_id' not in session:
        flash('You must be logged in to create a blog post', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        content_format = request.form.get('content_format', 'plain')  # Default to plain text
        picture = request.form.get('picture', 'filament.jpg')  # Default to filament.jpg
        
        # Basic validation
        if not title or not content:
            flash('Title and content are required', 'error')
            return render_template('blog_form.html', post={})
        
        # Create new blog post
        post = {
            'title': title,
            'content': content,
            'content_format': content_format,
            'category': category,
            'author_id': ObjectId(session['user_id']),  # Convert string to ObjectId
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'picture': picture
        }
        
        post_id = db.blog_posts.insert_one(post).inserted_id
        
        flash('Blog posted successfully!', 'success')
        return redirect(url_for('blog_detail', post_id=post_id))
    
    # GET request - show the form
    return render_template('blog_form.html', post={})

@app.route('/blog/edit/<post_id>', methods=['GET', 'POST'])
def blog_edit(post_id):
    # Check if user is logged in
    if 'user_id' not in session:
        flash('You must be logged in to edit a blog post', 'error')
        return redirect(url_for('login'))
    
    # Retrieve the post
    post = db.blog_posts.find_one({'_id': ObjectId(post_id)})
    
    if not post:
        flash('Blog post not found', 'error')
        return redirect(url_for('blog_list'))
    
    # Check if the current user is the author
    if str(post.get('author_id')) != session['user_id']:
        flash('You do not have permission to edit this post', 'error')
        return redirect(url_for('blog_detail', post_id=post_id))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        content_format = request.form.get('content_format', post.get('content_format', 'plain'))
        picture = request.form.get('picture', post.get('picture', 'filament.jpg'))
        
        # Basic validation
        if not title or not content:
            flash('Title and content are required', 'error')
            return render_template('blog_form.html', post=post)
        
        # Update the post
        db.blog_posts.update_one(
            {'_id': ObjectId(post_id)},
            {'$set': {
                'title': title,
                'content': content,
                'content_format': content_format,
                'category': category,
                'updated_at': datetime.now(),
                'picture': picture
            }}
        )
        
        flash('Blog post updated successfully!', 'success')
        return redirect(url_for('blog_detail', post_id=post_id))
    
    # GET request - show the form with existing data
    return render_template('blog_form.html', post=post)

@app.route('/blog/delete/<post_id>', methods=['POST'])
def blog_delete(post_id):
    # Check if user is logged in
    if 'user_id' not in session:
        flash('You must be logged in to delete a blog post', 'error')
        return redirect(url_for('login'))
    
    # Retrieve the post
    post = db.blog_posts.find_one({'_id': ObjectId(post_id)})
    
    if not post:
        flash('Blog post not found', 'error')
        return redirect(url_for('blog_list'))
    
    # Check if the current user is the author
    if str(post.get('author_id')) != session['user_id']:
        flash('You do not have permission to delete this post', 'error')
        return redirect(url_for('blog_detail', post_id=post_id))
    
    # Delete the post
    db.blog_posts.delete_one({'_id': ObjectId(post_id)})
    
    flash('Blog post deleted successfully!', 'success')
    return redirect(url_for('blog_list'))

# Admin route to initialize sample blog posts
@app.route('/admin/initialize_blog_data')
def initialize_blog_data():
    # Check if user is logged in and is admin
    if 'user_id' not in session:
        flash('You must be logged in to access this page', 'error')
        return redirect(url_for('login'))
    
    # Find the admin user
    admin_user = db.users.find_one({'email': 'admin@gogoprint.net'})
    if not admin_user:
        flash('Admin user not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Force clear existing blog posts
    db.blog_posts.delete_many({})
    
    # Sample blog data
    sample_posts = [
        {
            'title': 'Getting Started with 3D Printing: A Beginner\'s Guide',
            'content': """# Getting Started with 3D Printing

Are you intrigued by the world of 3D printing but don't know where to begin? This comprehensive guide will walk you through the essentials of 3D printing, from choosing your first printer to creating your initial models.

## Choosing Your First 3D Printer

When selecting your first 3D printer, consider these factors:

1. **Budget**: Entry-level printers start around $200, while more advanced models can cost $1,000+
2. **Build Volume**: Determines the maximum size of objects you can print
3. **Print Technology**: FDM (Fused Deposition Modeling) is most common for beginners
4. **Assembly Requirements**: Pre-assembled or DIY kit

## Essential Materials

Most beginners start with PLA (Polylactic Acid) filament because it's:
- Biodegradable
- Easy to print with
- Available in many colors
- Doesn't require a heated bed

## Software Needs

You'll need these software tools:
- **CAD Software**: To design 3D models (Fusion 360, Blender, TinkerCAD)
- **Slicer**: To prepare models for printing (Cura, PrusaSlicer)

## First Print Tips

1. Start with pre-made models from Thingiverse or Printables
2. Use a raft or brim for better bed adhesion
3. Watch the first layer to ensure proper adhesion
4. Start with smaller objects to minimize print time

Remember, 3D printing is a learning process. Don't get discouraged by initial failures - they're part of the journey!""",
            'content_format': 'markdown',
            'category': 'Beginners',
            'author_id': str(admin_user['_id']),
            'created_at': datetime.now() - timedelta(days=7),
            'updated_at': datetime.now() - timedelta(days=7),
            'picture': 'blog/beginner.webp'
        },
        {
            'title': 'Advanced Techniques for Perfect 3D Prints',
            'content': """# Advanced Techniques for Perfect 3D Prints

Once you've mastered the basics of 3D printing, it's time to level up your skills. This post explores advanced techniques that will help you achieve professional-quality prints.

## Fine-Tuning Your Print Settings

### Temperature Optimization

The perfect temperature varies by material and even by filament brand. Create a temperature tower to find your optimal settings:

1. Download a temperature tower STL file
2. Set up temperature changes at different heights in your slicer
3. Print and evaluate which temperature produces the best results

### Retraction Settings

Proper retraction settings eliminate stringing and oozing:
- Start with 5mm distance at 45mm/s for direct drive extruders
- For Bowden setups, try 6-7mm at 25-30mm/s
- Fine-tune in 0.5mm increments

## Post-Processing Techniques

Take your prints to the next level with these finishing methods:

1. **Sanding**: Start with 120 grit, then progress to 220, 400, and 600+ for a smooth finish
2. **Vapor Smoothing**: For ABS prints, use acetone vapor to create a glossy surface
3. **Priming and Painting**: Apply filler primer before painting to hide layer lines

## Advanced Materials

Beyond PLA and ABS, consider these specialty materials:

- **PETG**: Combines ease of printing with durability
- **TPU/TPE**: Flexible filaments for rubber-like parts
- **Carbon Fiber infused**: For rigid, lightweight parts
- **Wood/Metal filled**: For unique aesthetics

## Calibration is Key

Regularly calibrate these aspects of your printer:
- E-steps for precise extrusion
- Flow rate calibration for dimensional accuracy
- Bed leveling for perfect first layers

Remember, consistency is critical in 3D printing. Keep a log of your successful settings for each material and model type.""",
            'content_format': 'markdown',
            'category': 'Advanced',
            'author_id': str(admin_user['_id']),
            'created_at': datetime.now() - timedelta(days=5),
            'updated_at': datetime.now() - timedelta(days=5),
            'picture': 'blog/techniques.jpg'
        },
        {
            'title': 'Five Amazing 3D Printing Projects for Your Home',
            'content': """# Five Amazing 3D Printing Projects for Your Home

Put your 3D printer to work creating functional and decorative items for your home with these project ideas!

## 1. Customizable Drawer Organizers

Stop buying one-size-fits-all drawer organizers and print exactly what you need:

- Measure your drawer dimensions
- Design or find modular organizer systems
- Print in sections and arrange as needed

This approach works great for kitchen utensils, office supplies, and bathroom items.

## 2. Smart Home Device Mounts

Create perfect mounting solutions for your smart home devices:

- Wall mounts for Echo Dot or Google Home Mini
- Under-cabinet mounts for smart displays
- Custom camera mounts with perfect viewing angles

## 3. Planters with Integrated Drainage

Design beautiful planters with built-in functionality:

- Create nested designs with inner and outer pots
- Add proper drainage holes without mess
- Incorporate self-watering features with reservoirs

## 4. Custom Light Fixtures

Transform ordinary lights with 3D printed lampshades:

- Design geometric patterns for interesting shadow effects
- Use translucent filaments for diffused lighting
- Create modular designs that snap together

## 5. Functional Wall Art

Combine aesthetics and function with these ideas:

- Geometric wall planters
- Cable management systems that double as art
- Wall-mounted organizers with hidden storage

For each of these projects, consider using PETG for durability or specialty filaments like wood-filled PLA for unique textures and appearances. The possibilities are endless when you combine creativity with your 3D printer's capabilities!""",
            'content_format': 'markdown',
            'category': 'Projects',
            'author_id': str(admin_user['_id']),
            'created_at': datetime.now() - timedelta(days=3),
            'updated_at': datetime.now() - timedelta(days=3),
            'picture': 'blog/project.webp'
        },
        {
            'title': 'The Future of 3D Printing Technology',
            'content': """# The Future of 3D Printing Technology

The world of 3D printing is evolving rapidly, with new technologies emerging that promise to revolutionize manufacturing, medicine, construction, and more. Let's explore some of the most exciting developments on the horizon.

## Multi-Material Printing

Current consumer 3D printers typically print with one material at a time, but that's changing:

- Advanced multi-extruder systems allowing 4+ materials in a single print
- Material mixing nozzles creating gradients and blends
- Automatic filament changing systems for unlimited color combinations

These advancements will enable complex prints with varying properties throughout a single object.

## Metal Printing for the Masses

Metal 3D printing has traditionally required industrial equipment costing hundreds of thousands of dollars, but new approaches are making it more accessible:

- FDM printers using metal-infused filaments followed by sintering
- Desktop selective laser sintering (SLS) machines at increasingly affordable prices
- Metal injection modeling (MIM) techniques adapted for 3D printing

## Bioprinting Breakthroughs

The medical applications of 3D printing are perhaps the most revolutionary:

- Organ printing using patient's own cells to eliminate rejection
- Biocompatible scaffolds for tissue regeneration
- Custom medication printing with precise dosages and release profiles

## Construction-Scale Printing

3D printing is scaling up dramatically:

- Houses being printed in 24-48 hours
- Concrete formulations specifically designed for 3D printing
- Autonomous systems for printing infrastructure in remote or disaster areas

## AI and Automation

Artificial intelligence is making 3D printing more accessible:

- Automatic error detection and correction during printing
- Design generation from simple text descriptions
- Real-time optimization of print parameters

## What This Means for Hobbyists

As these technologies mature, we can expect:

1. More affordable access to advanced printing capabilities
2. Simplified workflows from idea to finished object
3. New creative possibilities with multi-material and hybrid manufacturing
4. Greater reliability and less waste

The next decade will transform 3D printing from a hobbyist technology to an essential manufacturing method across industries. Those who embrace and master these emerging technologies now will be well-positioned for the future.""",
            'content_format': 'markdown',
            'category': 'Technology',
            'author_id': str(admin_user['_id']),
            'created_at': datetime.now() - timedelta(days=1),
            'updated_at': datetime.now() - timedelta(days=1),
            'picture': 'blog/future_3d_printing.jpeg'
        },
        {
            'title': '7 Common 3D Printing Issues and How to Fix Them',
            'content': """# 7 Common 3D Printing Issues and How to Fix Them

Every 3D printing enthusiast encounters problems now and then. Here's how to troubleshoot the most common issues and get back to successful printing.

## 1. Poor Bed Adhesion

**Symptoms:** Print detaches from bed, warped bottom layer, failed print

**Solutions:**
- Clean your print bed thoroughly with isopropyl alcohol
- Adjust your nozzle height (first layer should be slightly squished)
- Try a bed adhesive like glue stick, hairspray, or specialized solutions
- Increase bed temperature by 5°C increments
- Add a brim or raft to increase surface contact

## 2. Stringing or Oozing

**Symptoms:** Thin strands of filament between parts of your print

**Solutions:**
- Optimize retraction settings (increase distance slightly, 5-7mm for Bowden, 2-4mm for direct drive)
- Lower printing temperature by 5-10°C
- Increase travel speed
- Enable "combing" or "avoid crossing perimeters" in your slicer
- Dry your filament if it's been exposed to humidity

## 3. Layer Shifting

**Symptoms:** Layers are misaligned in X or Y axis

**Solutions:**
- Check and tighten belts
- Ensure pulleys are secure on motor shafts
- Reduce printing speed
- Check for mechanical obstructions in the printer's movement
- Verify stepper driver current is appropriate

## 4. Under-extrusion

**Symptoms:** Gaps between lines, thin layers, or incomplete parts

**Solutions:**
- Increase flow rate (5-10%)
- Clear any partial nozzle clogs with a cold pull
- Check for filament grinding in the extruder
- Increase printing temperature
- Slow down printing speed

## 5. Overheating and Sagging

**Symptoms:** Drooping overhangs, "elephant's foot" at base, poor bridging

**Solutions:**
- Improve part cooling (upgrade fan, print cooling ducts)
- Lower printing temperature
- Reduce print speed for overhangs
- Use supports where necessary
- Enable "minimum layer time" settings in your slicer

## 6. Z-Banding or Ribbing

**Symptoms:** Horizontal lines or inconsistencies at regular intervals

**Solutions:**
- Lubricate Z-axis lead screws
- Check for bent lead screws
- Ensure Z-axis moves smoothly throughout its range
- Tighten any loose mechanical components
- Enable Z-hop during retraction if appropriate

## 7. Warping and Curling

**Symptoms:** Corners or edges lifting from the bed

**Solutions:**
- Ensure proper bed temperature (60-70°C for PLA, 90-110°C for ABS)
- Use an enclosure to maintain ambient temperature
- Add a brim or raft
- Reduce cooling fan speed for first few layers
- Use a draft shield feature in your slicer

Remember that 3D printing is often an exercise in patience and careful adjustment. Keep a log of your fixes so you know what works for future prints!""",
            'content_format': 'markdown',
            'category': 'Tips & Tricks',
            'author_id': str(admin_user['_id']),
            'created_at': datetime.now() - timedelta(days=2),
            'updated_at': datetime.now() - timedelta(days=2),
            'picture': 'blog/3d_printing_issues.jpg'
        },
        {
            'title': 'The Best Filaments for Functional 3D Prints',
            'content': """# The Best Filaments for Functional 3D Prints

Not all 3D printing materials are created equal. When you need parts that perform under stress or in specific environments, choosing the right filament is crucial. Here's a guide to selecting materials for functional prints.

## PETG: The Versatile Workhorse

**Ideal for:** General-purpose functional parts, outdoor use, food-safe applications (with proper post-processing)

**Properties:**
- Excellent layer adhesion and strength
- Good impact resistance
- Weather resistant
- Temperature resistant up to 80°C
- Low shrinkage and warping
- Relatively easy to print

PETG combines many of PLA's printing advantages with significantly better durability, making it perfect for parts like enclosures, tool holders, and mechanical components.

## Nylon: When Toughness is Critical

**Ideal for:** Moving parts, gears, hinges, snap-fits, tools

**Properties:**
- Exceptional toughness and durability
- Excellent wear resistance
- Good flexibility without breaking
- High temperature resistance (80-100°C)
- Low friction coefficient

The caveat: Nylon is hygroscopic (absorbs moisture) and can be challenging to print. Always dry before printing and consider using an enclosure.

## TPU/TPE: Flexible Solutions

**Ideal for:** Gaskets, grips, protective cases, vibration dampeners

**Properties:**
- Rubber-like flexibility (various shore hardness available)
- Excellent impact absorption
- Good abrasion resistance
- Chemical resistance
- Stretchy but returns to shape

TPU's flexibility makes it perfect when you need parts that compress, stretch, or absorb impact. Shore hardness values (e.g., 95A vs 85A) indicate stiffness.

## Polycarbonate (PC): Engineering-Grade Strength

**Ideal for:** High-strength components, transparent parts, high-temperature applications

**Properties:**
- Extremely high impact strength
- Optical clarity
- Heat resistant up to 110-115°C
- Excellent rigidity
- UV resistant

PC requires high temperatures (250-300°C) to print properly and benefits greatly from an enclosure to prevent warping.

## Carbon Fiber Composites: Rigidity Without Weight

**Ideal for:** Drone parts, robotics, structural components

**Properties:**
- Significantly increased stiffness
- Reduced weight compared to pure plastics
- Minimal flex and deformation
- Improved dimensional stability
- Unique matte finish

Carbon fiber composites (like CF-PLA, CF-PETG, or CF-Nylon) provide rigidity with less material, but are abrasive and require hardened nozzles.

## ASA: Outdoor Durability

**Ideal for:** Exterior parts, UV-exposed components, automotive applications

**Properties:**
- Excellent UV resistance (doesn't yellow or degrade)
- Weather resistant
- Impact resistant
- Heat resistant up to 90-100°C
- Matte finish with good aesthetics

Similar to ABS but with superior weather resistance, ASA is perfect for outdoor installations.

## Material Selection Tips

When choosing your material, consider these factors:

1. **Environmental conditions**: Temperature, UV exposure, moisture
2. **Mechanical requirements**: Flexibility, impact resistance, weight
3. **Printing difficulty**: Some materials need enclosures or special hardware
4. **Post-processing needs**: Will the part need to be finished or treated?
5. **Cost**: Specialty filaments can cost 3-5x more than basic PLA

Test your critical parts with small samples before committing to a full print. This ensures the material properties meet your specific requirements.""",
            'content_format': 'markdown',
            'category': 'Materials',
            'author_id': str(admin_user['_id']),
            'created_at': datetime.now() - timedelta(days=4),
            'updated_at': datetime.now() - timedelta(days=4),
            'picture': 'blog/filament.jpg'
        },
        {
            'title': 'Optimizing Print Speed: Finding the Perfect Balance',
            'content': """# Optimizing Print Speed: Finding the Perfect Balance

The eternal question in 3D printing: "How fast can I print without sacrificing quality?" This guide will help you find your printer's sweet spot for both speed and quality.

## Understanding Speed vs. Quality

Print speed affects:
- Print time (obviously)
- Surface quality
- Structural integrity
- Detail accuracy
- Adhesion between layers

The goal is finding the maximum speed that still delivers acceptable results for your specific needs.

## Key Speed-Related Settings

When optimizing for speed, these are the crucial settings to adjust:

### 1. Print Speed Hierarchy

Most slicers allow different speeds for different features:
- **Outer walls**: Slowest (20-40mm/s) for best surface quality
- **Inner walls**: Medium speed (40-60mm/s)
- **Infill**: Fastest (60-100mm/s) as it's hidden
- **Top/bottom layers**: Medium-slow (30-50mm/s) for good surface finish
- **Supports**: Fast (60-120mm/s) as appearance doesn't matter

### 2. Acceleration and Jerk Settings

Speed isn't just about mm/s values - it's also about how quickly your printer changes speed:
- **Acceleration**: How fast the printer reaches its target speed (500-3000mm/s²)
- **Jerk/Junction Deviation**: How abruptly the printer can change direction

Lower values mean smoother motion but longer print times. Higher values mean faster prints but potentially more artifacts.

## Hardware Considerations

Your maximum viable print speed depends heavily on your printer's hardware:

### Printer Frame Rigidity
- **CoreXY/Delta designs**: Generally handle higher speeds
- **Bed slingers (moving Y-axis)**: More limited by momentum
- **Rigidity mods**: Braces and reinforcements can help increase maximum speed

### Hotend Capacity
- **Standard hotends**: Limited to ~8-10mm³/s extrusion volume
- **High-flow hotends**: Can reach 15-40mm³/s
- **Volcano or other long melt zone hotends**: Essential for very fast printing

Remember: Speed is limited by how fast you can melt filament!

## Material-Specific Speed Guidelines

Different materials have different optimal speed ranges:

- **PLA**: Most forgiving, prints well at 60-100mm/s
- **PETG**: Benefits from slower speeds, 40-70mm/s
- **ABS/ASA**: 40-80mm/s with proper temperature control
- **TPU/Flexibles**: Very slow, 15-30mm/s
- **Composites (wood/metal filled)**: 30-50mm/s with larger nozzles

## My Speed Optimization Method

To find your printer's sweet spot:

1. **Create a speed test model**: A simple calibration cube or tower with controlled features
2. **Start conservative**: Begin with moderate speeds and gradually increase
3. **Test incrementally**: Raise speeds by 10-20% each test until quality suffers
4. **Inspect crucial features**: Look at overhangs, bridging, and surface quality
5. **Fine-tune feature-specific speeds**: Once you find the general limit, optimize individual feature speeds

## Advanced Speed Techniques

Once you've mastered basic speed settings, consider:

- **Pressure advance/linear advance**: Compensates for pressure in the nozzle during speed changes
- **Input shaping/resonance compensation**: Reduces ringing at higher speeds
- **Volumetric flow limiting**: Prevents over-extrusion by capping flow rate
- **Adaptive layer heights**: Thicker layers where possible, thinner where needed

## When to Prioritize Speed vs. Quality

- **Prototypes and test fits**: Maximum speed, minimum quality
- **Functional parts**: Balanced approach, focus on structural integrity
- **Display pieces**: Minimum speed, maximum quality
- **Production runs**: Find the highest speed that maintains acceptable quality

Remember, the fastest print is the one you don't have to print twice because it failed! Sometimes slowing down actually saves time overall.""",
            'content_format': 'markdown',
            'category': 'Advanced',
            'author_id': str(admin_user['_id']),
            'created_at': datetime.now() - timedelta(days=6),
            'updated_at': datetime.now() - timedelta(days=6),
            'picture': 'blog/print_speed.webp'
        },
        {
            'title': 'Eco-Friendly 3D Printing: Sustainable Practices for Makers',
            'content': """# Eco-Friendly 3D Printing: Sustainable Practices for Makers

3D printing has revolutionized prototyping and manufacturing, but it also creates environmental challenges. Here's how to make your 3D printing hobby more sustainable.

## Sustainable Filament Options

### Biodegradable Filaments

**PLA (Polylactic Acid)**
- Made from renewable resources like corn starch or sugar cane
- Biodegradable under industrial composting conditions
- Look for PLA brands that are certified compostable

**PHA (Polyhydroxyalkanoate)**
- Fully biodegradable, even in home composting
- Breaks down in marine environments
- Mechanical properties similar to traditional plastics

### Recycled Filaments

Several companies now offer filaments made from recycled plastic:
- Recycled PET from water bottles
- Reclaimed manufacturing waste
- Post-consumer plastic waste

These filaments turn waste into resources and generally have a smaller carbon footprint.

## Minimizing Waste

### Print Design Optimization

- Use gyroid or honeycomb infill patterns (stronger with less material)
- Design parts to minimize or eliminate support structures
- Verify sizing in software before printing
- Test with small prototypes before full-sized prints

### Failed Print Management

- Grind failed prints to create recycled filament
- Consider investing in a filament recycler for your workshop
- Save failed prints for future recycling programs

### Support Material Solutions

- Design prints to eliminate or minimize supports
- Use soluble supports (PVA, HIPS) where appropriate
- Consider printing orientation carefully to reduce support needs

## Energy Efficiency

### Printer Efficiency

- Insulate your printer with an enclosure to reduce heat loss
- Consider using higher speed/lower quality settings for non-critical parts
- Maintain your printer for optimal performance
- Group prints to maximize bed usage (but be cautious about increased risk)

### Renewable Energy

- Power your printer with solar panels if possible
- Schedule prints during times when renewable energy is more prevalent in your grid
- Consider carbon offsets for your printing power consumption

## Material Life Cycle

### Extending Print Lifespan

- Apply proper post-processing to increase durability
- Design for repairability with modular components
- Use appropriate materials for the application to prevent premature failure

### End-of-Life Considerations

- Design objects for disassembly and recycling
- Label parts with recycling information
- Keep different materials separate in multi-material designs

## Community Initiatives

### Collaborative Consumption

- Share printers through makerspaces and libraries
- Print on-demand rather than speculatively
- Organize filament exchanges with other makers

### Education and Awareness

- Teach sustainable 3D printing practices
- Share designs that minimize environmental impact
- Document and promote your sustainability efforts

## The Bigger Picture

Remember that the most sustainable print is often the one you don't make. Before printing, ask yourself:

1. Is this object necessary?
2. Could it be made with less material?
3. Will it be used long-term or quickly discarded?
4. Could I repair an existing object instead?

By combining thoughtful consumption with sustainable materials and practices, we can enjoy the benefits of 3D printing while minimizing its environmental impacts. The maker community has always been innovative - let's apply that creativity to sustainability as well.""",
            'content_format': 'markdown',
            'category': 'Tips & Tricks',
            'author_id': str(admin_user['_id']),
            'created_at': datetime.now() - timedelta(days=6),
            'updated_at': datetime.now() - timedelta(days=6),
            'picture': 'blog/sustainable.jpeg'
        },
        {
            'title': 'Calibrating Your 3D Printer: The Ultimate Guide',
            'content': """# Calibrating Your 3D Printer: The Ultimate Guide

A well-calibrated 3D printer produces accurate, consistent, and high-quality prints. This comprehensive guide will walk you through the essential calibration procedures every 3D printing enthusiast should master.

## Why Calibration Matters

Proper calibration:
- Improves dimensional accuracy
- Enhances surface finish
- Reduces print failures
- Minimizes troubleshooting time
- Extends printer lifespan

## Essential Calibration Procedures

### 1. Bed Leveling

The foundation of good prints is a properly leveled bed.

**Manual Leveling Process:**
1. Heat bed to printing temperature
2. Home all axes
3. Disable steppers
4. Use paper test at each corner (paper should have slight resistance)
5. Check center point
6. Repeat process at least twice

**Automatic Bed Leveling:**
1. Ensure probe offset is correctly set
2. Verify Z-offset using paper test
3. Save settings to EEPROM
4. Still check occasionally with manual tests

### 2. Extruder Calibration (E-steps)

Ensures your printer extrudes exactly the amount of filament it should.

**Procedure:**
1. Mark filament 120mm from entry point
2. Heat nozzle to printing temperature
3. Command extrusion of 100mm
4. Measure remaining distance to mark
5. Calculate new E-steps: 
   ```
   New E-steps = Current E-steps × (100 ÷ Actual distance extruded)
   ```
6. Set new value and save to EEPROM
7. Verify with another 100mm test

### 3. Flow Rate Calibration

Fine-tunes extrusion for specific filaments.

**Procedure:**
1. Print a 20mm calibration cube with 2 perimeters, 0% infill
2. Measure wall thickness with calipers
3. Calculate flow rate:
   ```
   New flow rate = (Designed wall thickness ÷ Measured thickness) × Current flow rate
   ```
4. Save this value in your slicer profile for this specific filament

### 4. Temperature Calibration

**Temperature Tower Test:**
1. Download or create a temperature tower model
2. Set temperature changes at different heights in your slicer
3. Print and evaluate results
4. Look for best layer adhesion, minimal stringing, good bridging
5. Record optimal temperature for each filament type

### 5. Retraction Calibration

Prevents stringing and oozing.

**Procedure:**
1. Print retraction test models (multiple towers or strings)
2. Start with default settings (5mm at 45mm/s for Bowden, 1.5mm at 35mm/s for direct drive)
3. Adjust in 0.5mm increments
4. Find minimum retraction distance that prevents stringing
5. Then optimize retraction speed

### 6. Acceleration and Jerk Tuning

Balances print speed with quality.

**Procedure:**
1. Print calibration patterns with features to show ringing/ghosting
2. Start with conservative values
3. Gradually increase until quality deteriorates
4. Set values just below the point where quality suffers
5. Consider different values for different print features

### 7. Linear Advance/Pressure Advance

Compensates for pressure in the nozzle during speed changes.

**Procedure:**
1. Print recommended test pattern for your firmware
2. Start with K-factor of 0
3. Test incremental values according to firmware documentation
4. Select K-factor showing most consistent extrusion at corners
5. Implement in start G-code or firmware settings

## Creating Your Calibration Workflow

Develop a systematic approach:

1. **Initial setup**: Bed leveling, E-steps, basic temperature settings
2. **Per-filament calibration**: Flow rate, temperature tuning, retraction
3. **Maintenance calibration**: Check bed level and E-steps monthly
4. **Advanced tuning**: Linear advance, acceleration, jerk as needed

## Documenting Your Settings

Keep detailed records of:
- E-steps value
- Flow rates for each filament
- Temperature profiles
- Retraction settings by material
- Linear advance K-factors

Storing these in a spreadsheet or notebook ensures you can quickly set up optimal parameters for any project.

## Calibration Test Models

These test prints help diagnose specific issues:
- **Calibration cube**: Dimensional accuracy
- **Benchy**: Overall print quality
- **Overhang test**: Cooling and speed settings
- **Bridging test**: Bridging capabilities
- **Retraction tower**: Stringing issues
- **Tolerance test**: Fitment accuracy

Remember, calibration is not a one-time process but an ongoing refinement. As your printer ages, parts wear, and you try new materials, recalibration helps maintain optimal performance.""",
            'content_format': 'markdown',
            'category': 'Beginners',
            'author_id': str(admin_user['_id']),
            'created_at': datetime.now() - timedelta(days=8),
            'updated_at': datetime.now() - timedelta(days=8),
            'picture': 'blog/calibrating.png'
        }
    ]
    
    # Insert sample blog posts
    result = db.blog_posts.insert_many(sample_posts)
    
    return redirect(url_for('blog_list'))

if __name__ == '__main__':
    # Create indexes for better performance
    db.users.create_index('email', unique=True)
    app.run(debug=True, port=5001)