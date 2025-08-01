from transformers import BertTokenizer, BertForSequenceClassification
import torch
from huggingface_hub import login

import pandas as pd
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build as GoogleAPIClientBuild

load_dotenv()
api_service_name = "youtube"
api_version = "v3"
API_KEY = os.getenv("YOUTUBE_API_KEY")

def fetch_comments(video_id):
    dir_path = "backend\\extracted_comments\\"

    file_path = dir_path+f"{video_id}.csv"
    print("Start Scrapping")
    try:
        youtube = GoogleAPIClientBuild(
            api_service_name,api_version,developerKey=API_KEY
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

        df = pd.DataFrame(comments,columns=['like_count','comment'])
        df.to_csv(file_path,index=False)
        print("Comments Exacted. And to this file path: "+file_path)
        return file_path, len(comments)
    except Exception as e:
        return f"An Error has occur: {e}"

login(os.getenv("HG_TOKEN"))
model_name = 'ganeshkharad/gk-hinglish-sentiment'
tokenizer = BertTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(model_name) 
model.eval()

def predict_sentiment(comment):
    inputs = tokenizer(comment, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        label = torch.argmax(outputs.logits, dim=1).item()
    mapping = {0: "negative", 1: "neutral", 2: "positive"}
    return mapping[label]

def analyze_sentiment(video_id):
    try:
        # Simulate fetching comments from a video ID
        file_path,_ = r"backend\extracted_comments\Wg6JSTlROMg.csv",10
        
        if not file_path:
            return None
        data = pd.read_csv(file_path)
        if data.empty:
            return None
        data['sentiment'] = data['comment'].astype(str).apply(predict_sentiment)
        sentiment_counts = data['sentiment'].value_counts().to_dict()
        if not sentiment_counts:
            return None
        print(sentiment_counts)
        return sentiment_counts
        
    except Exception as e:
        print(f"Error analyzing sentiment: {e}")
        return None

