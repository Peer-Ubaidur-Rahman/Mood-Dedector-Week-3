from flask import Blueprint, request, jsonify
from routes_auth import token_required
from db_init import get_db_connection

mood_bp = Blueprint('mood', __name__)

@mood_bp.route('/mood-records', methods=['POST'])
@token_required
def create_mood_record(current_user_id):
    """Create a new mood record"""
    data = request.get_json()
    
    if not data or not data.get('emotion') or data.get('confidence') is None:
        return jsonify({'message': 'Missing required fields'}), 400
    
    emotion = data['emotion']
    confidence = float(data['confidence'])
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO mood_records (user_id, emotion, confidence) VALUES (?, ?, ?)',
            (current_user_id, emotion, confidence)
        )
        conn.commit()
        record_id = cursor.lastrowid
        conn.close()
        
        return jsonify({
            'message': 'Mood record created successfully',
            'record_id': record_id
        }), 201
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

@mood_bp.route('/mood-records', methods=['GET'])
@token_required
def get_mood_records(current_user_id):
    """Get all mood records for current user"""
    limit = request.args.get('limit', 100, type=int)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, emotion, confidence, timestamp FROM mood_records WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?',
        (current_user_id, limit)
    )
    records = cursor.fetchall()
    conn.close()
    
    mood_list = []
    for record in records:
        mood_list.append({
            'id': record[0],
            'emotion': record[1],
            'confidence': record[2],
            'timestamp': record[3]
        })
    
    return jsonify(mood_list), 200

@mood_bp.route('/mood-records/<int:record_id>', methods=['GET'])
@token_required
def get_mood_record(current_user_id, record_id):
    """Get a specific mood record"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, user_id, emotion, confidence, timestamp FROM mood_records WHERE id = ?',
        (record_id,)
    )
    record = cursor.fetchone()
    conn.close()
    
    if not record:
        return jsonify({'message': 'Record not found'}), 404
    
    if record[1] != current_user_id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    return jsonify({
        'id': record[0],
        'emotion': record[2],
        'confidence': record[3],
        'timestamp': record[4]
    }), 200

@mood_bp.route('/mood-records/<int:record_id>', methods=['DELETE'])
@token_required
def delete_mood_record(current_user_id, record_id):
    """Delete a mood record"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM mood_records WHERE id = ?', (record_id,))
    record = cursor.fetchone()
    
    if not record:
        conn.close()
        return jsonify({'message': 'Record not found'}), 404
    
    if record[0] != current_user_id:
        conn.close()
        return jsonify({'message': 'Unauthorized'}), 403
    
    cursor.execute('DELETE FROM mood_records WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Record deleted successfully'}), 200

@mood_bp.route('/stats/emotions', methods=['GET'])
@token_required
def get_emotion_stats(current_user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT emotion, COUNT(*) as count, AVG(confidence) as avg_confidence
        FROM mood_records
        WHERE user_id = ?
        GROUP BY emotion
        ORDER BY count DESC
    ''', (current_user_id,))
    stats = cursor.fetchall()
    conn.close()
    
    emotion_stats = []
    for stat in stats:
        emotion_stats.append({
            'emotion': stat[0],
            'count': stat[1],
            'avg_confidence': round(stat[2], 2)
        })
    
    return jsonify(emotion_stats), 200
