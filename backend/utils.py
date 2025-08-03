from dotenv import load_dotenv
from googleapiclient.discovery import build as GoogleAPIClientBuild
from huggingface_hub import InferenceClient

import re
import html

import pandas as pd
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build as GoogleAPIClientBuild
import google.generativeai as genai
import json

import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend for matplotlib   
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import io 
import requests

# Load environment variables
load_dotenv()
api_service_name = "youtube"
api_version = "v3"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
HG_TOKEN = os.getenv("HG_TOKEN")
TOKEN = os.getenv("TOKEN")
STORE_ID = os.getenv("STORE_ID")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize the Hugging Face model and tokenizer
client = InferenceClient(model="ganeshkharad/gk-hinglish-sentiment", token=HG_TOKEN)

import warnings
warnings.filterwarnings("ignore", message=".*encoder_attention_mask.*")


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
        raise ValueError("Data is empty, cannot generate graphs.")

    graphs_urls = {}

    def upload_to_vercel_blob(image_buffer, filename):
        image_buffer.seek(0)
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/octet-stream"
        }
        url = f"https://blob.vercel-storage.com/api/v1/blobs/{STORE_ID}/{filename}?access=public"
        resp = requests.put(url, headers=headers, data=image_buffer)
        resp.raise_for_status()
        return resp.json().get("url")

    # ========= Pie Chart =========
    color_map = {
        "positive": "gold",
        "neutral": "lightskyblue",
        "negative": "lightcoral"
    }

    sentiment_order = ["positive", "neutral", "negative"]
    labels = [s for s in sentiment_order if s in data['sentiment'].values]
    sizes = [data['sentiment'].value_counts().get(s, 0) for s in labels]
    colors = [color_map[s] for s in labels]

    explode = [0.1 if s == "positive" else 0 for s in labels]

    fig_pie, ax_pie = plt.subplots(figsize=(6, 6))
    fig_pie.patch.set_alpha(0)  # Transparent background
    ax_pie.set_facecolor('none')
    ax_pie.pie(sizes, explode=explode, labels=labels, colors=colors,
            autopct='%1.1f%%', shadow=True, startangle=140)
    ax_pie.axis('equal')

    buf_pie = io.BytesIO()
    fig_pie.savefig(buf_pie, format='png', transparent=True, bbox_inches='tight')
    plt.close(fig_pie)
    graphs_urls['pie_chart'] = upload_to_vercel_blob(buf_pie, f"pie_{video_id}.png")


    # ========= Word Cloud =========
    text = ' '.join(data['comment'].astype(str).tolist())
    wordcloud = WordCloud(width=800, height=400, background_color=None, mode="RGBA").generate(text)
    buf_wc = io.BytesIO()
    wordcloud.to_image().save(buf_wc, format='PNG')
    graphs_urls['word_cloud'] = upload_to_vercel_blob(buf_wc, f"word_cloud_{video_id}.png")

    # ========= Bar Chart =========
    avg_likes = data.groupby('sentiment')['likecount'].mean().reset_index()
    fig_bar, ax_bar = plt.subplots(figsize=(10, 6))
    fig_bar.patch.set_alpha(0)  # Transparent background
    ax_bar.set_facecolor('none')
    ax_bar.bar(avg_likes['sentiment'], avg_likes['likecount'], color=colors)
    ax_bar.set_xlabel('Sentiment')
    ax_bar.set_ylabel('Average Like Count')
    buf_bar = io.BytesIO()
    fig_bar.savefig(buf_bar, format='png', transparent=True, bbox_inches='tight')
    plt.close(fig_bar)
    graphs_urls['bar_chart'] = upload_to_vercel_blob(buf_bar, f"bar_{video_id}.png")

    return graphs_urls

def predict_sentiment(comment):
    try:
        result = client.text_classification(comment)
        if result and len(result) > 0:
            return result[0]['label'].lower()
        return 'neutral'
    except Exception as e:
        raise ValueError(f"Error predicting sentiment: {e}")

def generateInsights(data):
    if data.empty:
        raise ValueError("No comments Found, cannot generate insights.")
    
    comments_text = ' '.join(data['comment'].astype(str).tolist())
    max_length = 8000
    if len(comments_text) > max_length:
        comments_text = comments_text[:max_length] + '...'
    
    prompt = f"""
    You are an assistant that analyzes user comments from a YouTube video to extract viewer engagement insights.
    Only output information strictly present in the comments without adding any hallucinated content.
    Analyze the following list of YouTube comments and generate insights.
    Your output MUST be a valid JSON object. Do not include any text before or after the JSON object.

    Based on the comments provided:
    1.  Identify and extract a maximum of the top three most relevant and frequently asked questions.
    2.  If NO questions are asked, provide a brief, one-sentence summary of the overall viewer engagement (e.g., "Viewers are highly engaged and positive, frequently praising the content's clarity.").
    3.  Analyze all comments for suggestions or desires for future content and provide the top three video suggestions. For each suggestion, estimate the percentage of viewers who showed interest if possible, or describe the level of interest.
    4.  Your response MUST strictly be based on the provided comments. Do not invent questions or suggestions.

    **Output Format:**

    If questions are found, use this JSON structure:
      "Question": ["string", "string", "string"],
      "Suggestion": ["string", "string", "string"]
    If NO questions are found, use this JSON structure:
      "Engagement": ["string", "string", "string"]
      "Suggestion": ["string", "string", "string"]
    Here are the comments:
    ---
    {comments_text}
    ---
    """
    model = genai.GenerativeModel("gemma-3n-e2b-it")
    response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.2, max_output_tokens=1000))

    try:
        insights = json.loads(response.text.replace("```", "")[4:])
        if 'Question' in insights:
            insights = {
                "Questions": insights.get('Question', []),
                "Suggestions": insights.get('Suggestion', [])
            }
        else:
            insights = {
                "Engagement": insights.get('Engagement', []),
                "Suggestions": insights.get('Suggestion', [])
            }
        return insights
    except Exception as e:
        raise ValueError(f"Error generating insights: {e}")