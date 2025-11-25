from flask import Flask, jsonify, request, abort
from flask_cors import CORS
import os, json, time, secrets
from utils import (
    fetch_comments,
    clean_comment,
    generateGraphs,
    predict_sentiment,
    generateInsights,
)

try:
    import redis
    REDIS_AVAIABLE = True
except Exception:
    REDIS_AVAIABLE = False

# Configurable via env vars
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", 10 * 60))  
SINGLE_USE = os.getenv("SESSION_SINGLE_USE", "true").lower() in ("1", "true", "yes")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

if REDIS_AVAIABLE:
    REDIS_URL = os.getenv("REDIS_URL","redis://localhost:6379/0")
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
else:
    _local_store = {}


# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*":{"origins":CORS_ORIGINS}}) # Enable CORS for all routes



def make_session_id():
    return secrets.token_urlsafe(16)

def save_session(sid, payload_obj):
    payload_json = json.dumps(payload_obj)
    if REDIS_AVAIABLE:
        redis_client.setex(f"sid:{sid}", SESSION_TTL_SECONDS, payload_json)
    else:
        expires_at = time.time() + SESSION_TTL_SECONDS
        _local_store[sid] = (payload_json, expires_at)

def get_session(sid, consume):
    if REDIS_AVAIABLE:
        key = f"sid:{sid}"
        data = redis_client.get(key)

        if data is None:
            return None
        if consume and SINGLE_USE:
            redis_client.delete(key)
        return json.loads(data)
    else:
        entry = _local_store.get(sid)
        if not entry:
            return None
        payload_json, expries_at = entry
        if time.time() > expries_at:
            _local_store.pop(sid, None)
            return None
        if consume and SINGLE_USE:
            _local_store.pop(sid, None)
        return json.loads(payload_json)
    
@app.route("/session", methods=["POST"])
def create_session():
    try:
        body = request.get_json(force=True, silent=True)
        if not body or "payload" not in body:
            return jsonify({"error": "payload is required"}), 400
        payload = body["payload"]
        sid = make_session_id()
        save_session(sid, payload)
        return jsonify({"session_id": sid, "expires_in": SESSION_TTL_SECONDS}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/session/<sid>", methods=["GET"])
def fetch_session(sid):
    try:
        data = get_session(sid, consume=True)
        if data is None:
            return jsonify({"error": "not found or expired"}), 404
        return jsonify({"data": data}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500




@app.route("/", methods=['GET'])
def home(): 
    return jsonify({"message": "Welcome to the Sentilytics API!"})


@app.route("/analyze/<video_id>", methods=['GET'])
def analyze_video(video_id):
    try:
        print(f"Fetching comments for video ID: {video_id}")
        data, video_title = fetch_comments(video_id)
        print(f"Fetched {len(data)} comments for video ID: {video_id}")
        if data.empty:
            return jsonify({"error": "No comments found for this video."}), 404
        
        # Clean comments and predict sentiment
        data['comment'] = data['comment'].astype(str).apply(clean_comment)
        data['sentiment'] = data['comment'].astype(str).apply(predict_sentiment)

        sentiment_counts = data['sentiment'].value_counts().to_dict()
        sentiment_counts["totalComments"] = len(data) or 1
        sentiment_counts["video_title"] = video_title
        print(sentiment_counts)
        return jsonify(sentiment_counts)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/dashboard/<video_id>', methods=['GET'])
def generateReportRoute(video_id):
    try:
        print(f"Fetching comments for video ID: {video_id}")
        data, video_title = fetch_comments(video_id)
        print(f"Fetched {len(data)} comments for video ID: {video_id}")
        if data.empty:
            return jsonify({"error": "No comments found for this video."}), 404
        
        # Clean comments and predict sentiment
        data['comment'] = data['comment'].astype(str).apply(clean_comment)
        data['sentiment'] = data['comment'].astype(str).apply(predict_sentiment)

        print("Generating graphs...")
        graphs_urls = generateGraphs(data, video_id) if not data.empty else None
        print("Graphs generated successfully.")

        print("Generating insights...")
        insights = generateInsights(data)
        print("Insights generated successfully.")


        sentiment_counts = data['sentiment'].value_counts().to_dict()
        sentiment_counts = {
            "positive": sentiment_counts.get('positive', 0),
            "negative": sentiment_counts.get('negative', 0),
            "neutral": sentiment_counts.get('neutral', 0),
        } # In case of missing sentiment, default to 0


        return jsonify({
            "video_title":video_title,
            "totalComments": len(data),
            "sentimentCounts": sentiment_counts,
            "graph_urls": graphs_urls,
            "top_liked_comments":{
                "top_liked_comment":data.nlargest(1,'likecount').to_dict(orient='records'),
                "positive": data[data['sentiment'] == 'positive'].nlargest(1, 'likecount').to_dict(orient='records'),
                "negative": data[data['sentiment'] == 'negative'].nlargest(1, 'likecount').to_dict(orient='records'),
                "neutral": data[data['sentiment'] == 'neutral'].nlargest(1, 'likecount').to_dict(orient='records')
            },
            "insight": insights
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True, port=5000)