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
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import google.generativeai as genai
import json
import requests

import warnings
warnings.filterwarnings("ignore", message=".*encoder_attention_mask.*")


# Load environment variables
load_dotenv()
api_service_name = "youtube"
api_version = "v3"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
HG_TOKEN = os.getenv("HG_TOKEN")
VERCEL_BLOB_READ_WRITE_TOKEN = os.getenv("VERCEL_BLOB_READ_WRITE_TOKEN")
VERCEL_BLOB_STORE_ID = os.getenv("VERCEL_BLOB_STORE_ID")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
# Initialize the Hugging Face model and tokenizer
login(HG_TOKEN)
model_name = 'ganeshkharad/gk-hinglish-sentiment'
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(model_name) 
model.eval()


# Configure Google Generative AI
genai.configure(api_key=GEMINI_API_KEY)

# Initialize Flask app
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

@app.route('/analyze/<video_id>', methods=['GET'])
def generateReportRoute(video_id):
    try:
        print(f"Fetching comments for video ID: {video_id}")
        data = fetch_comments(video_id)
        print(f"Fetched {len(data)} comments for video ID: {video_id}")
        if data.empty:
            return jsonify({"error": "No comments found for this video."}), 404
        
        # Clean comments and predict sentiment
        data['comment'] = data['comment'].astype(str).apply(clean_comment)
        data['sentiment'] = data['comment'].astype(str).apply(predict_sentiment)

        print("Generating graphs...")
        graphs_urls = generateGraphs(data, video_id, VERCEL_BLOB_READ_WRITE_TOKEN, VERCEL_BLOB_STORE_ID) if not data.empty else None
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
            "totalComments": len(data),
            "sentimentCounts": sentiment_counts,
            "graph_urls": graphs_urls,
            "top_liked_comments":{
                "positive": data[data['sentiment'] == 'positive'].nlargest(1, 'likecount').to_dict(orient='records'),
                "negative": data[data['sentiment'] == 'negative'].nlargest(1, 'likecount').to_dict(orient='records'),
                "neutral": data[data['sentiment'] == 'neutral'].nlargest(1, 'likecount').to_dict(orient='records')
            },
            "insight": insights
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    app.run(debug=True)