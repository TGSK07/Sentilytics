from transformers import BertTokenizer, BertForSequenceClassification
import torch
from huggingface_hub import login

import re
import html

import pandas as pd
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build as GoogleAPIClientBuild

import matplotlib.pyplot as plt
from wordcloud import WordCloud
import io 

load_dotenv()
api_service_name = "youtube"
api_version = "v3"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def fetch_comments(video_id):
    try:
        youtube = GoogleAPIClientBuild(
            api_service_name,api_version,developerKey=YOUTUBE_API_KEY
        )

        comments = []
        next_page_token = None

        while True:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId = video_id,
                maxResults = 1000,
                pageToken = next_page_token
                )
            
            response = request.execute()

            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']
                comments.append([
                    comment['likeCount'],
                    comment['textDisplay']
                ])

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        df = pd.DataFrame(comments,columns=['likecount','comment'])

        return df
    
    except Exception as e:
        raise Exception(f"Error fetching comments: {e}")

login(os.getenv("HG_TOKEN"))
model_name = 'ganeshkharad/gk-hinglish-sentiment'
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(model_name) 
model.eval()


def clean_comment(comment):
    # 1. Remove HTML tags
    comment = re.sub(r'<.*?>', '', comment)
    
    # 2. Remove links (URLs)
    comment = re.sub(r'http\S+|www\S+|https\S+', '', comment)
    
    # 3. Unescape HTML entities (&amp; -> &, &#39; -> ')
    comment = html.unescape(comment)
    
    # 4. Remove extra whitespace
    comment = re.sub(r'\s+', ' ', comment).strip()
    
    return comment

def generateGraphs(data, video_id):
    if data.empty:
        return None
    if not os.path.exists('backend/graphs'):
        os.makedirs('backend/graphs')

    graphs_urls = {}

    # ========= Pie Chart =========
    labels = data['sentiment'].value_counts().index.tolist()
    sizes = data['sentiment'].value_counts().values.tolist()
    colors  = ['gold', 'lightcoral', 'lightskyblue']
    explode = (0.1, 0, 0)  

    plt.pie(sizes, explode=explode, labels=labels, colors=colors,
            autopct='%1.1f%%', shadow=True, startangle=140)
    plt.axis('equal')
    buf_pie = io.BytesIO()
    plt.savefig(buf_pie, format='png', transparent=True, bbox_inches='tight')
    plt.close()
    resp = blob.put(f"pie_{video_id}.png", buf_pie, options={"addRandomSuffix":"false", "access":"public"})
    graphs_urls['pie_chart'] = resp.get('url')

    # ========= Word Cloud =========
    text = ' '.join(data['comment'].astype(str).tolist())
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    buf_wc = io.BytesIO()
    buf_wc.seek(0)
    resp = blob.put(f"word_cloud_{video_id}.png", buf_wc, options={"addRandomSuffix":"false", "access":"public"})
    graphs_urls['word_cloud'] = resp.get('url')

    # ========= Bar Chart =========
    avg_likes = data.groupby('sentiment')['likecount'].mean().reset_index()
    plt.figure(figsize=(10, 6))
    plt.bar(avg_likes['sentiment'], avg_likes['likecount'], color=colors)
    plt.xlabel('Sentiment')
    plt.ylabel('Average Like Count')
    plt.title('Average Like Count per Sentiment')
    buf_bar = io.BytesIO()
    buf_bar.seek(0)
    resp = blob.put(f"bar_{video_id}.png", buf_bar, options={"addRandomSuffix":"false", "access":"public"})
    graphs_urls['bar_chart'] = resp.get('url')

    return graphs_urls

def predict_sentiment(comment):
    inputs = tokenizer(comment, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        label = torch.argmax(outputs.logits, dim=1).item()
    mapping = {0: "negative", 1: "neutral", 2: "positive"}
    return mapping[label]

def generateInsights(data):
    if data.empty:
        return None
    
    data['comment'] = data['comment'].astype(str).apply(clean_comment)
    data['sentiment'] = data['comment'].astype(str).apply(predict_sentiment)

    sentiment_counts = data['sentiment'].value_counts().to_dict()
    
    if not sentiment_counts:
        return None
    
    return {
        "totalComments": len(data),
        "sentimentCounts": sentiment_counts,
        "graph_urls": generateGraphs(data, video_id) if not data.empty else None,
    }


def generateReport(video_id):
    try:
        data = fetch_comments(video_id)
        
        if data.empty:
            return None
        
        data['comment'] = data['comment'].astype(str).apply(clean_comment)
        data['sentiment'] = data['comment'].astype(str).apply(predict_sentiment)

        sentiment_counts = data['sentiment'].value_counts().to_dict()
        
        if not sentiment_counts:
            return None
        
        return jsonify({
            "totalComments": len(data),
            "sentimentCounts": sentiment_counts,
            "graph_urls": generateGraphs(data, video_id) if not data.empty else None,

        })
        
    except Exception as e:
        print(f"Error analyzing sentiment: {e}")
        return None
