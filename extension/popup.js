// Element references
const startBtn = document.getElementById('start-analysis');
const statusMsg = document.getElementById('status');
const initialView = document.getElementById('initial-view');
const resultsView = document.getElementById('results-view');
const detailsLink = document.getElementById('view-details-link');

// Bar and label references
const sentiments = [
    {
        key: 'positive',
        bar: document.querySelector('.bar.positive'),
        value: document.querySelector('.percentage-value.positive'),
        tooltip: document.querySelector('.bar.positive + .hover-tooltip'),
    },
    {
        key: 'neutral',
        bar: document.querySelector('.bar.neutral'),
        value: document.querySelector('.percentage-value.neutral'),
        tooltip: document.querySelector('.bar.neutral + .hover-tooltip'),
    },
    {
        key: 'negative',
        bar: document.querySelector('.bar.negative'),
        value: document.querySelector('.percentage-value.negative'),
        tooltip: document.querySelector('.bar.negative + .hover-tooltip'),
    }
];

// Backend base URL
const BACKEND_URL = "http://localhost:5000";

// Function to extract YouTube video ID from URL
function getYouTubeVideoId(url) {
    try {
        const regExp = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
        const match = url.match(regExp);
        return match ? match[1] : null;
    } catch (e) {
        return null;
    }
}

// Helper functions
function setSentimentBar(type, percent) {
    const sentiment = sentiments.find(s => s.key === type);
    if (!sentiment) return;
    sentiment.bar.style.width = percent + '%';
    sentiment.value.textContent = percent + '%';
    sentiment.tooltip.textContent = percent + '%';
}

function resetBars() {
    sentiments.forEach(s => {
        s.bar.style.width = '0%';
        s.value.textContent = '0%';
        s.tooltip.textContent = '0%';
    });
}

function showLoading() {
    statusMsg.textContent = "Analyzing...";
    statusMsg.style.display = "block";
    startBtn.disabled = true;
}

function hideLoading() {
    statusMsg.textContent = "";
    statusMsg.style.display = "none";
    startBtn.disabled = false;
}

function showResults() {
    initialView.classList.add('hidden');
    resultsView.classList.remove('hidden');
}

function showInitial() {
    resultsView.classList.add('hidden');
    initialView.classList.remove('hidden');
    hideLoading();
    resetBars();
}

// Get current tab YouTube URL with Chrome extension API (Manifest V3/V2 compatible)
async function getCurrentYouTubeURL() {
    return new Promise((resolve) => {
        if (chrome && chrome.tabs) {
            chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
                const url = tabs[0]?.url || '';
                resolve(url);
            });
        } else {
            resolve('');
        }
    });
}

// Main workflow
startBtn.addEventListener('click', async () => {
    resetBars();
    showLoading();

    // 1. Get YouTube video URL from tab
    const url = await getCurrentYouTubeURL();

    if (!url.includes("youtube.com") && !url.includes("youtu.be")) {
        statusMsg.textContent = "Please open a YouTube video.";
        startBtn.disabled = false;
        return;
    }

    // 2. Extract video ID
    const videoId = getYouTubeVideoId(url);

    if (!videoId) {
        statusMsg.textContent = "Invalid YouTube URL or missing video ID.";
        startBtn.disabled = false;
        return;
    }

    try {
        // 3. Call backend for analysis using video ID in endpoint
        const response = await fetch(`${BACKEND_URL}/analyze/${videoId}`, { method: "GET" });

        if (!response.ok) throw new Error("Server Error");

        const data = await response.json();

        // data expected: { positive: 70, neutral: 22, negative: 8, details_url: "..." }
        setTimeout(() => {
            setSentimentBar('positive', data.positive);
            setSentimentBar('neutral', data.neutral);
            setSentimentBar('negative', data.negative);
        }, 200);

        // Activate "View Detailed Trends" link
        if (data.details_url) {
            detailsLink.href = data.details_url;
        } else {
            detailsLink.href = "http://localhost:5000"; // fallback
        }

        hideLoading();
        showResults();

    } catch (err) {
        statusMsg.textContent = "Failed to fetch analysis. " + (err.message || "");
        startBtn.disabled = false;
    }
});

// Always start with the initial view on load
window.addEventListener('DOMContentLoaded', () => {
    showInitial();
});
