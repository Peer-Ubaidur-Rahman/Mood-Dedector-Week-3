from flask import Flask, jsonify, request
from flask_cors import CORS
from db_init import init_db, get_db_connection
from routes_auth import auth_bp, token_required
from routes_mood import mood_bp

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'

init_db()

app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(mood_bp, url_prefix='/api')

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'API is running'}), 200

@app.route('/api/users/<int:user_id>', methods=['GET'])
@token_required
def get_user(current_user_id, user_id):
    """Get user profile"""
    if current_user_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, fullname, email, created_at FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    return jsonify({
        'id': user[0],
        'fullname': user[1],
        'email': user[2],
        'created_at': user[3]
    }), 200

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@token_required
def update_user(current_user_id, user_id):
    """Update user profile"""
    if current_user_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if data.get('fullname'):
        cursor.execute('UPDATE users SET fullname = ? WHERE id = ?', (data['fullname'], user_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'User updated successfully'}), 200

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user_id, user_id):
    """Delete user account"""
    if current_user_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM mood_records WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'User deleted successfully'}), 200

@app.route('/api/sessions', methods=['POST'])
@token_required
def create_session(current_user_id):
    """Start a new detection session"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO sessions (user_id) VALUES (?)', (current_user_id,))
        conn.commit()
        session_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'message': 'Session started',
            'session_id': session_id
        }), 201
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/sessions/<int:session_id>', methods=['PUT'])
@token_required
def update_session(current_user_id, session_id):
    """Update session (end time, emotions detected)"""
    data = request.get_json()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM sessions WHERE id = ?', (session_id,))
        session = cursor.fetchone()
        
        if not session or session[0] != current_user_id:
            conn.close()
            return jsonify({'message': 'Unauthorized'}), 403
        
        if data.get('emotions_detected') is not None:
            cursor.execute(
                'UPDATE sessions SET emotions_detected = ? WHERE id = ?',
                (data['emotions_detected'], session_id)
            )
        
        if data.get('end_session'):
            cursor.execute(
                'UPDATE sessions SET end_time = CURRENT_TIMESTAMP WHERE id = ?',
                (session_id,)
            )
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Session updated'}), 200
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@app.route('/api/sessions', methods=['GET'])
@token_required
def get_sessions(current_user_id):
    """Get all sessions for current user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, duration, emotions_detected, start_time, end_time FROM sessions WHERE user_id = ? ORDER BY start_time DESC',
        (current_user_id,)
    )
    sessions = cursor.fetchall()
    conn.close()
    
    session_list = []
    for session in sessions:
        session_list.append({
            'id': session[0],
            'duration': session[1],
            'emotions_detected': session[2],
            'start_time': session[3],
            'end_time': session[4]
        })
    
    return jsonify(session_list), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
