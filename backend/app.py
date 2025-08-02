from flask import Flask, jsonify
from flask_cors import CORS

from utils import (
    fetch_comments,
    clean_comment,
    generateGraphs,
    predict_sentiment,
    generateInsights,
)

from transformers import BertTokenizer, BertForSequenceClassification
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build as GoogleAPIClientBuild
from huggingface_hub import login
import torch
import io
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from vercel_blob import VercelBlob

# Load environment variables
load_dotenv()
api_service_name = "youtube"
api_version = "v3"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
HG_TOKEN = os.getenv("HG_TOKEN")
VERCEL_BLOB_READ_WRITE_TOKEN = os.getenv("VERCEL_BLOB_READ_WRITE_TOKEN")
VERCEL_BLOB_STORE_ID = os.getenv("VERCEL_BLOB_STORE_ID")

# Initialize the Hugging Face model and tokenizer
login(HG_TOKEN)
model_name = 'ganeshkharad/gk-hinglish-sentiment'
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(model_name) 
model.eval()

# Initialize Vercel Blob for storing graphs
blob = VercelBlob(token=VERCEL_BLOB_READ_WRITE_TOKEN, store=VERCEL_BLOB_STORE_ID)

# Initialize Flask app
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

@app.route('/fetch_comments/<video_id>', methods=['GET'])
def generateReportRoute(video_id):
    try:
        data = fetch_comments(video_id)
        if data.empty:
            return jsonify({"error": "No comments found for this video."}), 404
        
        # Clean comments and predict sentiment
        data['comment'] = data['comment'].astype(str).apply(clean_comment)
        data['sentiment'] = data['comment'].astype(str).apply(predict_sentiment)

        sentiment_counts = data['sentiment'].value_counts().to_dict()
        sentiment_counts = {
            "positive": sentiment_counts.get('positive', 0),
            "negative": sentiment_counts.get('negative', 0),
            "neutral": sentiment_counts.get('neutral', 0)
        } # In case of missing sentiment, default to 0

        return jsonify({
            "totalComments": len(data),
            "sentimentCounts": sentiment_counts,
            "graph_urls": generateGraphs(data, video_id) if not data.empty else None,
            "top_liked_comments":{
                "positive": data[data['sentiment'] == 'positive'].nlargest(1, 'likecount').to_dict(orient='records'),
                "negative": data[data['sentiment'] == 'negative'].nlargest(1, 'likecount').to_dict(orient='records'),
                "neutral": data[data['sentiment'] == 'neutral'].nlargest(1, 'likecount').to_dict(orient='records')
            },
            "ai_insights": generateInsights(data)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    app.run(debug=True)