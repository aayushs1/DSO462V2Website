from flask import Flask, render_template, request, jsonify, session
import os
from datetime import datetime, timedelta
import uuid
import random

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'gogoprint_secret_key_dev')

# Mock database using dictionaries
mock_db = {
    'chats': [],
    'messages': []
}

# Manual curated chat data with image filenames

def make_chat(chat_id, title, user_message, bot_response, model_name, image_filename):
    now = datetime.now()
    return {
        'chat': {
            'id': chat_id,
            '_id': chat_id,
            'title': title,
            'user_id': 'philbert_loekman',
            'created_at': now,
            'last_updated': now + timedelta(minutes=2),
            'image': image_filename
        },
        'messages': [
            {
                'id': str(uuid.uuid4()),
                'chat_id': chat_id,
                'sender': 'user',
                'content': user_message,
                'timestamp': now
            },
            {
                'id': str(uuid.uuid4()),
                'chat_id': chat_id,
                'sender': 'bot',
                'content': bot_response,
                'model_preview': True,
                'model_name': model_name,
                'model_size': f"{random.randint(1, 5)}.{random.randint(1,9)} MB",
                'timestamp': now + timedelta(minutes=1)
            }
        ]
    }

chats_data = [
    make_chat(
        str(uuid.uuid4()),
        "Cable chaos turned classy",
        "Can you help me design a desktop cable management system that hides USB hubs, has clips for routing, and fits behind a dual-monitor stand?",
        "I've created a 3D model that emphasizes hidden compartments and snap-fit assembly. It should neatly tuck under most desk edges and includes cable clips optimized for standard 5mm cables.",
        "desktop_cable_management.stl",
        "desktop_cable_management.png"
    ),
    make_chat(
        str(uuid.uuid4()),
        "Light it up with angles",
        "I'm looking for a geometric lampshade that gives cool shadows and works with standard IKEA sockets.",
        "Here’s your 3D model! The geometric patterns maximize light diffusion while keeping structural integrity. It prints without supports and has a twist-lock base compatible with most E26 sockets.",
        "geometric_lampshade.stl",
        "geometric_lampshade.png"
    ),
    make_chat(
        str(uuid.uuid4()),
        "Desk Tetris 3000",
        "I want a modular desk organizer that lets me stack and rearrange compartments for pens, sticky notes, and USBs.",
        "Your modular system features interlocking connections and a minimalist design. Each tray nests snugly, and optional hooks allow it to hang off shelves too!",
        "modular_desk_organizer.stl",
        "modular_desk_organizer.png"
    ),
    make_chat(
        str(uuid.uuid4()),
        "Lazy stand, active grip",
        "Can you design a phone holder I can use at the gym treadmill? Needs to tilt, grip tight, and have cable pass-through.",
        "This stand features an ergonomic grip and ventilation slots for sweaty sessions. I added a hidden compartment for earbuds and a channel to hold your charger in place.",
        "phone_holder.stl",
        "phone_holder.png"
    )
]

def load_curated_chat_data():
    curated_chats = []
    curated_messages = []

    for entry in chats_data:
        curated_chats.append(entry['chat'])
        curated_messages.extend(entry['messages'])

    mock_db['chats'] = curated_chats
    mock_db['messages'] = curated_messages

@app.route('/')
def index():
    session['user_id'] = 'philbert_loekman'
    session['user_name'] = "Philbert Loekman"
    session['user_email'] = "philbert@loekman.com"

    recent_chats = mock_db['chats'][:5]
    return render_template('index.html', recent_chats=recent_chats, user_name=session.get('user_name'), user_email=session.get('user_email'))

@app.route('/chat/<chat_id>')
def view_chat(chat_id):
    if 'user_id' not in session:
        session['user_id'] = 'philbert_loekman'
        session['user_name'] = "Philbert Loekman"
        session['user_email'] = "philbert@loekman.com"

    chat = next((c for c in mock_db['chats'] if c['id'] == chat_id), None)
    if not chat:
        return "Chat not found", 404

    messages = [msg for msg in mock_db['messages'] if msg.get('chat_id') == chat_id]
    messages.sort(key=lambda x: x.get('timestamp'))
    recent_chats = mock_db['chats'][:5]

    return render_template('chat.html', chat=chat, messages=messages, recent_chats=recent_chats, user_name=session.get('user_name'), user_email=session.get('user_email'))

@app.route('/chat/new', methods=['POST'])
def new_chat():
    user_id = session.get('user_id', 'philbert_loekman')
    chat_id = str(uuid.uuid4())
    new_chat = {
        'id': chat_id,
        '_id': chat_id,
        'title': 'New Chat',
        'user_id': user_id,
        'created_at': datetime.now(),
        'last_updated': datetime.now()
    }
    mock_db['chats'].insert(0, new_chat)
    return jsonify({'chat_id': chat_id})

@app.route('/message/send', methods=['POST'])
def send_message():
    data = request.json
    chat_id = data.get('chat_id')
    message_text = data.get('message')
    if not chat_id or not message_text:
        return jsonify({'error': 'Missing required fields'}), 400

    now = datetime.now()
    user_message = {
        'id': str(uuid.uuid4()),
        'chat_id': chat_id,
        'sender': 'user',
        'content': message_text,
        'timestamp': now
    }
    mock_db['messages'].append(user_message)

    for chat in mock_db['chats']:
        if chat['id'] == chat_id and chat['title'] == 'New Chat':
            title = ' '.join(message_text.split()[:5])
            chat['title'] = (title[:27] + '...') if len(title) > 30 else title
            chat['last_updated'] = now
            break

    bot_response = {
        'id': str(uuid.uuid4()),
        'chat_id': chat_id,
        'sender': 'bot',
        'content': f"Here's a quick draft based on your message: {message_text}",
        'model_preview': True,
        'model_name': f"generated_model_{chat_id[:6]}.stl",
        'model_size': f"{random.randint(1, 5)}.{random.randint(1, 9)} MB",
        'timestamp': now + timedelta(seconds=2)
    }
    mock_db['messages'].append(bot_response)

    for chat in mock_db['chats']:
        if chat['id'] == chat_id:
            chat['last_updated'] = now + timedelta(seconds=2)
            mock_db['chats'].remove(chat)
            mock_db['chats'].insert(0, chat)
            break

    bot_response_json = bot_response.copy()
    bot_response_json['timestamp'] = bot_response_json['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        'user_message_id': user_message['id'],
        'bot_message_id': bot_response['id'],
        'bot_response': bot_response_json
    })

@app.route('/load-curated-chats')
def load_curated_chats():
    load_curated_chat_data()
    return jsonify({
        'status': 'Loaded curated chat dataset',
        'chat_count': len(mock_db['chats'])
    })

if __name__ == '__main__':
    load_curated_chat_data()
    app.run(debug=True, port=5001)
