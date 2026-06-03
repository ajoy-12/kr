# app.py - Complete Flask Backend for KR IT Agency with Chatbot Logging
# Save this file as app.py in the same folder as your index.html
# Run with: python app.py

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import mysql.connector
from mysql.connector import Error
import jwt
import datetime
import re
import os
from functools import wraps

app = Flask(__name__, static_folder='.', static_url_path='')

# ==================== CONFIGURATION ====================
app.config['SECRET_KEY'] = 'krit_agency_secret_key_2024'
app.config['JWT_SECRET'] = 'krit_jwt_secret_key_2024'
app.config['JWT_EXPIRATION_HOURS'] = 24

# MySQL Configuration (XAMPP/WAMP)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''  # XAMPP default is empty, change if you set a password
app.config['MYSQL_DATABASE'] = 'krit_agency_db'

# Initialize extensions
CORS(app, origins=['http://localhost:5000', 'http://127.0.0.1:5000', 'http://localhost:5500'])
bcrypt = Bcrypt(app)


# ==================== DATABASE FUNCTIONS ====================
def get_db_connection():
    """Create and return a database connection"""
    try:
        connection = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DATABASE'],
            autocommit=True,
            use_pure=True
        )
        return connection
    except Error as e:
        print(f"❌ Database connection error: {e}")
        return None


def init_database():
    """Initialize database tables and insert sample data"""
    conn = get_db_connection()
    if not conn:
        print("\n" + "=" * 60)
        print("❌ DATABASE CONNECTION FAILED!")
        print("=" * 60)
        print("\nPlease make sure:")
        print("1. XAMPP/WAMP is installed and running")
        print("2. MySQL service is started")
        print("3. MySQL is running on port 3306")
        print("\nIf you have a MySQL password, update it in app.config['MYSQL_PASSWORD']")
        print("=" * 60)
        return False

    cursor = conn.cursor()

    # Create database if not exists
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {app.config['MYSQL_DATABASE']}")
    cursor.execute(f"USE {app.config['MYSQL_DATABASE']}")

    # Create users table (for admin login)
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS users
                   (
                       id
                       INT
                       AUTO_INCREMENT
                       PRIMARY
                       KEY,
                       username
                       VARCHAR
                   (
                       50
                   ) UNIQUE NOT NULL,
                       password_hash VARCHAR
                   (
                       255
                   ) NOT NULL,
                       email VARCHAR
                   (
                       100
                   ),
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       )
                   """)

    # Create contacts table (for form submissions)
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS contacts
                   (
                       id
                       INT
                       AUTO_INCREMENT
                       PRIMARY
                       KEY,
                       name
                       VARCHAR
                   (
                       100
                   ) NOT NULL,
                       email VARCHAR
                   (
                       100
                   ) NOT NULL,
                       service_type VARCHAR
                   (
                       100
                   ),
                       message TEXT NOT NULL,
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       is_read BOOLEAN DEFAULT FALSE
                       )
                   """)

    # Create portfolio table (for projects)
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS portfolio
                   (
                       id
                       INT
                       AUTO_INCREMENT
                       PRIMARY
                       KEY,
                       title
                       VARCHAR
                   (
                       200
                   ) NOT NULL,
                       category VARCHAR
                   (
                       50
                   ) NOT NULL,
                       description TEXT,
                       image_url VARCHAR
                   (
                       500
                   ),
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       )
                   """)

    # Create service_requests table
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS service_requests
                   (
                       id
                       INT
                       AUTO_INCREMENT
                       PRIMARY
                       KEY,
                       client_name
                       VARCHAR
                   (
                       100
                   ) NOT NULL,
                       client_email VARCHAR
                   (
                       100
                   ) NOT NULL,
                       service_type VARCHAR
                   (
                       100
                   ) NOT NULL,
                       details TEXT,
                       status VARCHAR
                   (
                       50
                   ) DEFAULT 'pending',
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                       )
                   """)

    # Create chat_logs table for chatbot conversations
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS chat_logs
                   (
                       id
                       INT
                       AUTO_INCREMENT
                       PRIMARY
                       KEY,
                       session_id
                       VARCHAR
                   (
                       100
                   ) NOT NULL,
                       user_message TEXT,
                       bot_response TEXT,
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       INDEX idx_session
                   (
                       session_id
                   ),
                       INDEX idx_created
                   (
                       created_at
                   )
                       )
                   """)
    print("✅ Chat logs table created")

    # Insert default admin user (username: admin, password: admin123)
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        password_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')
        cursor.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (%s, %s, %s)",
            ('admin', password_hash, 'admin@krit.com')
        )
        print("✅ Default admin created - Username: admin, Password: admin123")

    # Insert 20 portfolio items if table is empty
    cursor.execute("SELECT COUNT(*) FROM portfolio")
    count = cursor.fetchone()[0]
    if count == 0:
        portfolio_items = [
            ('E-commerce Platform Pro', 'Web Development', 'Full-stack e-commerce solution with payment integration',
             'https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=400&h=250&fit=crop'),
            ('AI Customer Support Bot', 'AI Automation', 'Intelligent chatbot with NLP capabilities',
             'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=400&h=250&fit=crop'),
            ('Luxury Brand Identity', 'Graphic Design', 'Complete brand identity package for luxury brand',
             'https://images.unsplash.com/photo-1541701494587-cb58502866ab?w=400&h=250&fit=crop'),
            ('E-commerce SEO Campaign', 'SEO Optimization', '200% organic traffic increase in 4 months',
             'https://images.unsplash.com/photo-1432888498266-38ffec3eaf0a?w=400&h=250&fit=crop'),
            ('Product Launch Video', 'Video Editing', 'Professional product launch promotional video',
             'https://images.unsplash.com/photo-1536240474400-3e3a5c3d0e9d?w=400&h=250&fit=crop'),
            ('Fintech Dashboard', 'Web Development', 'Real-time financial analytics dashboard',
             'https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=400&h=250&fit=crop'),
            ('Social Media Management AI', 'AI Automation', 'Automated social media posting and analytics',
             'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=400&h=250&fit=crop'),
            ('Mobile App UI/UX', 'Graphic Design', 'Modern mobile app interface design',
             'https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?w=400&h=250&fit=crop'),
            ('Local Business SEO', 'SEO Optimization', 'Local search domination for restaurant chain',
             'https://images.unsplash.com/photo-1555421689-491a97ff2040?w=400&h=250&fit=crop'),
            ('Corporate Training Video', 'Video Editing', 'Professional corporate training series',
             'https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=400&h=250&fit=crop'),
            ('Healthcare Portal', 'Web Development', 'Patient management and appointment system',
             'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=400&h=250&fit=crop'),
            ('Inventory Automation', 'AI Automation', 'Smart inventory management system',
             'https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=400&h=250&fit=crop'),
            ('Restaurant Branding', 'Graphic Design', 'Complete restaurant brand identity',
             'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=400&h=250&fit=crop'),
            ('International SEO', 'SEO Optimization', 'Global SEO strategy for expansion',
             'https://images.unsplash.com/photo-1527689368864-3a821dbccc34?w=400&h=250&fit=crop'),
            ('Wedding Highlight Reel', 'Video Editing', 'Cinematic wedding highlight video',
             'https://images.unsplash.com/photo-1519225421980-715cb0215aed?w=400&h=250&fit=crop'),
            ('Real Estate Platform', 'Web Development', 'Property listing and management system',
             'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=400&h=250&fit=crop'),
            ('Email Automation AI', 'AI Automation', 'Smart email marketing automation',
             'https://images.unsplash.com/photo-1557200134-90327ee9fafa?w=400&h=250&fit=crop'),
            ('Packaging Design', 'Graphic Design', 'Eco-friendly product packaging design',
             'https://images.unsplash.com/photo-1535016120720-40c646be5580?w=400&h=250&fit=crop'),
            ('Technical SEO Audit', 'SEO Optimization', 'Complete technical SEO optimization',
             'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=400&h=250&fit=crop'),
            ('Music Video Production', 'Video Editing', 'Professional music video editing',
             'https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=400&h=250&fit=crop')
        ]
        for item in portfolio_items:
            cursor.execute("""
                           INSERT INTO portfolio (title, category, description, image_url)
                           VALUES (%s, %s, %s, %s)
                           """, item)
        print("✅ 20 sample portfolio items added")

    conn.close()
    print("✅ Database initialized successfully!")
    return True


# ==================== JWT AUTH DECORATOR ====================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({'success': False, 'message': 'Token is missing!'}), 401

        if token.startswith('Bearer '):
            token = token[7:]

        try:
            data = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
            current_user = data['username']
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': 'Token has expired!'}), 401
        except:
            return jsonify({'success': False, 'message': 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


# ==================== CHATBOT API ENDPOINTS ====================

@app.route('/api/chat/save', methods=['POST'])
def save_chat_message():
    """Save chatbot conversation to database"""
    try:
        data = request.get_json()

        session_id = data.get('session_id', '')
        user_message = data.get('user_message', '')
        bot_response = data.get('bot_response', '')

        if not session_id or not user_message:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = conn.cursor()
        cursor.execute("""
                       INSERT INTO chat_logs (session_id, user_message, bot_response)
                       VALUES (%s, %s, %s)
                       """, (session_id, user_message, bot_response))

        conn.close()

        return jsonify({'success': True, 'message': 'Chat saved successfully'}), 200

    except Exception as e:
        print(f"Error saving chat: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/chat/logs', methods=['GET'])
@token_required
def get_chat_logs(current_user):
    """Get all chatbot conversations (admin only)"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
                       SELECT *
                       FROM chat_logs
                       ORDER BY created_at DESC LIMIT 500
                       """)
        chats = cursor.fetchall()

        for chat in chats:
            if chat.get('created_at'):
                chat['created_at'] = chat['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        conn.close()
        return jsonify({'success': True, 'data': chats, 'count': len(chats)}), 200

    except Exception as e:
        print(f"Error fetching chat logs: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/chat/sessions', methods=['GET'])
@token_required
def get_chat_sessions(current_user):
    """Get unique chat sessions with statistics (admin only)"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
                       SELECT session_id,
                              MIN(created_at)                   as first_message,
                              MAX(created_at)                   as last_message,
                              COUNT(*)                          as message_count,
                              COUNT(DISTINCT DATE (created_at)) as days_active
                       FROM chat_logs
                       GROUP BY session_id
                       ORDER BY last_message DESC
                       """)
        sessions = cursor.fetchall()

        for session in sessions:
            if session.get('first_message'):
                session['first_message'] = session['first_message'].strftime('%Y-%m-%d %H:%M:%S')
            if session.get('last_message'):
                session['last_message'] = session['last_message'].strftime('%Y-%m-%d %H:%M:%S')

        conn.close()
        return jsonify({'success': True, 'data': sessions, 'total_sessions': len(sessions)}), 200

    except Exception as e:
        print(f"Error fetching sessions: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/chat/session/<session_id>', methods=['GET'])
@token_required
def get_chat_session(current_user, session_id):
    """Get specific chat session messages (admin only)"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
                       SELECT *
                       FROM chat_logs
                       WHERE session_id = %s
                       ORDER BY created_at ASC
                       """, (session_id,))
        messages = cursor.fetchall()

        for msg in messages:
            if msg.get('created_at'):
                msg['created_at'] = msg['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        conn.close()
        return jsonify({'success': True, 'data': messages, 'session_id': session_id, 'count': len(messages)}), 200

    except Exception as e:
        print(f"Error fetching session: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/chat/stats', methods=['GET'])
@token_required
def get_chat_stats(current_user):
    """Get chatbot statistics (admin only)"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)

        # Total conversations
        cursor.execute("SELECT COUNT(*) as total FROM chat_logs")
        total = cursor.fetchone()

        # Unique sessions
        cursor.execute("SELECT COUNT(DISTINCT session_id) as unique_sessions FROM chat_logs")
        sessions = cursor.fetchone()

        # Today's chats
        cursor.execute("SELECT COUNT(*) as today FROM chat_logs WHERE DATE(created_at) = CURDATE()")
        today = cursor.fetchone()

        # Last 7 days
        cursor.execute(
            "SELECT COUNT(*) as last_week FROM chat_logs WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
        last_week = cursor.fetchone()

        # Most active session
        cursor.execute("""
                       SELECT session_id, COUNT(*) as message_count
                       FROM chat_logs
                       GROUP BY session_id
                       ORDER BY message_count DESC LIMIT 1
                       """)
        top_session = cursor.fetchone()

        conn.close()

        return jsonify({'success': True, 'data': {
            'total_messages': total['total'] if total else 0,
            'unique_sessions': sessions['unique_sessions'] if sessions else 0,
            'today_messages': today['today'] if today else 0,
            'last_week_messages': last_week['last_week'] if last_week else 0,
            'most_active_session': top_session
        }}), 200

    except Exception as e:
        print(f"Error fetching chat stats: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== CONTACT API ENDPOINTS ====================

@app.route('/api/contact', methods=['POST'])
def submit_contact():
    """Save contact form data to MySQL"""
    try:
        data = request.get_json()

        # Validation
        required_fields = ['name', 'email', 'message']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400

        # Email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = conn.cursor()
        cursor.execute("""
                       INSERT INTO contacts (name, email, service_type, message)
                       VALUES (%s, %s, %s, %s)
                       """, (data['name'], data['email'], data.get('service_type', ''), data['message']))

        conn.close()

        return jsonify({'success': True, 'message': 'Message sent successfully!'}), 201

    except Exception as e:
        print(f"Error in contact submission: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/messages', methods=['GET'])
@token_required
def get_messages(current_user):
    """Retrieve all contact messages (admin only)"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM contacts ORDER BY created_at DESC")
        messages = cursor.fetchall()

        for msg in messages:
            if msg.get('created_at'):
                msg['created_at'] = msg['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        conn.close()
        return jsonify({'success': True, 'data': messages}), 200

    except Exception as e:
        print(f"Error fetching messages: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
@token_required
def delete_message(current_user, message_id):
    """Delete a contact message (admin only)"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = conn.cursor()
        cursor.execute("DELETE FROM contacts WHERE id = %s", (message_id,))
        affected_rows = cursor.rowcount
        conn.close()

        if affected_rows > 0:
            return jsonify({'success': True, 'message': 'Message deleted successfully'}), 200
        else:
            return jsonify({'success': False, 'message': 'Message not found'}), 404

    except Exception as e:
        print(f"Error deleting message: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/login', methods=['POST'])
def admin_login():
    """Admin authentication"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password required'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.check_password_hash(user['password_hash'], password):
            token = jwt.encode({
                'username': username,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=app.config['JWT_EXPIRATION_HOURS'])
            }, app.config['JWT_SECRET'], algorithm='HS256')

            return jsonify({'success': True, 'token': token, 'message': 'Login successful'}), 200
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    except Exception as e:
        print(f"Error in login: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    """Fetch all portfolio items"""
    try:
        conn = get_db_connection()
        if not conn:
            fallback_portfolio = [
                {'id': i, 'title': f'Project {i}', 'category': 'Web Development',
                 'description': 'Sample project description',
                 'image': 'https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=400&h=250&fit=crop'}
                for i in range(1, 21)
            ]
            return jsonify({'success': True, 'data': fallback_portfolio, 'fallback': True}), 200

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, title, category, description, image_url FROM portfolio ORDER BY created_at DESC")
        portfolio = cursor.fetchall()
        conn.close()

        formatted_portfolio = []
        for item in portfolio:
            formatted_portfolio.append({
                'id': item['id'],
                'title': item['title'],
                'category': item['category'],
                'description': item['description'],
                'image': item['image_url']
            })

        return jsonify({'success': True, 'data': formatted_portfolio}), 200

    except Exception as e:
        print(f"Error fetching portfolio: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/portfolio/categories', methods=['GET'])
def get_portfolio_categories():
    """Get all unique portfolio categories"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': True,
                            'data': ['Web Development', 'AI Automation', 'Graphic Design', 'SEO Optimization',
                                     'Video Editing']}), 200

        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM portfolio ORDER BY category")
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()

        return jsonify({'success': True, 'data': categories}), 200

    except Exception as e:
        print(f"Error fetching categories: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/services/request', methods=['POST'])
def request_service():
    """Submit a service request"""
    try:
        data = request.get_json()

        required_fields = ['client_name', 'client_email', 'service_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['client_email']):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = conn.cursor()
        cursor.execute("""
                       INSERT INTO service_requests (client_name, client_email, service_type, details)
                       VALUES (%s, %s, %s, %s)
                       """, (data['client_name'], data['client_email'], data['service_type'], data.get('details', '')))

        conn.close()
        return jsonify({'success': True, 'message': 'Service request submitted successfully!'}), 201

    except Exception as e:
        print(f"Error in service request: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/service-requests', methods=['GET'])
@token_required
def get_service_requests(current_user):
    """Get all service requests (admin only)"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM service_requests ORDER BY created_at DESC")
        requests = cursor.fetchall()

        for req in requests:
            if req.get('created_at'):
                req['created_at'] = req['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        conn.close()
        return jsonify({'success': True, 'data': requests}), 200

    except Exception as e:
        print(f"Error fetching service requests: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get website statistics"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': True, 'data': {
                'total_contacts': 0,
                'total_portfolio': 20,
                'total_service_requests': 0,
                'total_chat_messages': 0
            }}), 200

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM contacts")
        contacts_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM portfolio")
        portfolio_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM service_requests")
        requests_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chat_logs")
        chat_count = cursor.fetchone()[0]

        conn.close()

        return jsonify({'success': True, 'data': {
            'total_contacts': contacts_count,
            'total_portfolio': portfolio_count,
            'total_service_requests': requests_count,
            'total_chat_messages': chat_count
        }}), 200

    except Exception as e:
        print(f"Error fetching stats: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'KR IT API is running',
        'timestamp': datetime.datetime.now().isoformat()
    }), 200


# ==================== SERVE FRONTEND ====================
@app.route('/')
def serve_index():
    """Serve the main HTML file"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return jsonify({
            'message': 'Frontend file not found. Please make sure index.html is in the same directory as app.py',
            'api_endpoints': {
                'POST /api/contact': 'Submit contact form',
                'POST /api/login': 'Admin login',
                'GET /api/messages': 'Get messages (admin)',
                'DELETE /api/messages/<id>': 'Delete message (admin)',
                'GET /api/portfolio': 'Get portfolio items',
                'POST /api/services/request': 'Submit service request',
                'GET /api/chat/logs': 'Get chatbot conversations (admin)',
                'GET /api/chat/sessions': 'Get chat sessions (admin)',
                'GET /api/chat/stats': 'Get chat statistics (admin)',
                'POST /api/chat/save': 'Save chat message',
                'GET /api/stats': 'Website statistics',
                'GET /api/health': 'Health check'
            },
            'admin_credentials': {
                'username': 'admin',
                'password': 'admin123'
            }
        }), 200


# ==================== RUN SERVER ====================
if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("   🚀 KR IT AGENCY - BACKEND SERVER")
    print("=" * 60)

    print("\n🔌 Connecting to MySQL...")
    if init_database():
        print("\n" + "=" * 60)
        print("   ✅ SERVER READY")
        print("=" * 60)
        print(f"\n📍 Frontend URL: http://localhost:5000")
        print(f"📍 API Base URL: http://localhost:5000/api")
        print(f"\n🔐 Admin Login Credentials:")
        print(f"   Username: admin")
        print(f"   Password: admin123")
        print(f"\n📡 Available API Endpoints:")
        print(f"   POST   /api/contact          - Send contact message")
        print(f"   POST   /api/login            - Admin login")
        print(f"   GET    /api/messages         - View contact messages (admin)")
        print(f"   DELETE /api/messages/<id>    - Delete message (admin)")
        print(f"   GET    /api/portfolio        - Get 20 portfolio items")
        print(f"   POST   /api/services/request - Request a service")
        print(f"   GET    /api/chat/logs        - View chatbot conversations (admin)")
        print(f"   GET    /api/chat/sessions    - View chat sessions (admin)")
        print(f"   GET    /api/chat/stats       - Chat statistics (admin)")
        print(f"   POST   /api/chat/save        - Save chat message")
        print(f"   GET    /api/stats            - Website statistics")
        print(f"   GET    /api/health           - Health check")
        print("\n" + "=" * 60)
        print("   Press Ctrl+C to stop the server")
        print("=" * 60 + "\n")

        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("\n" + "=" * 60)
        print("   ❌ DATABASE CONNECTION FAILED")
        print("=" * 60)
        print("\nTroubleshooting steps:")
        print("1. Open XAMPP/WAMP Control Panel")
        print("2. Click 'Start' next to MySQL")
        print("3. Wait for MySQL to start (port 3306)")
        print("4. If you have a MySQL password, update line 28 in app.py")
        print("5. Run 'python app.py' again")
        print("\nYour frontend will still work with fallback data!")
        print("=" * 60)

        print("\n⚠️  Running in FRONTEND-ONLY mode...")
        print("📍 Frontend URL: http://localhost:5000")
        print("\n" + "=" * 60)
        app.run(debug=True, host='0.0.0.0', port=5000)