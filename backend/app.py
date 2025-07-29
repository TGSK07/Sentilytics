from flask import Flask, request, jsonify
from flask_cors import CORS
from utils import analyze_sentiment
app = Flask(__name__)
CORS(app)

@app.route('/api/analyze/<str:video_id>', methods=['GET'])
def analyze():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL parameter is required"}), 400
    
    sentiment = analyze_sentiment(url)
    if sentiment is None:
        return jsonify({"error": "Failed to analyze sentiment"}), 500
    return jsonify({"sentiment": sentiment})

if __name__ == '__main__':
    app.run(debug=True)