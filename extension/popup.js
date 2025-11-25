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
]

// Backend base URL
const BACKEND_URL = "http://127.0.0.1:5000";
const HOMEPAGE_URL = "https://sentilytics-ebon.vercel.app";

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
        const response = await fetch(`${BACKEND_URL}/dashboard/${videoId}`, { method: "GET" });

        if (!response.ok) throw new Error("Server Error");

        const data = await response.json();

        // data expected: { positive: 70, neutral: 22, negative: 8, details_url: "..." }
        setTimeout(() => {
            total = data.totalComments || 1;
            setSentimentBar('positive', Math.round((data.sentimentCounts.positive / total) * 100));
            setSentimentBar('neutral', Math.round((data.sentimentCounts.neutral / total) * 100));
            setSentimentBar('negative', Math.round((data.sentimentCounts.negative / total) * 100));
        }, 200);

        // Activate "View Detailed Trends" link
        if (data && Object.keys(data).length) {
            // keep local sessionStorage copy (doesn't change your current logic)
            sessionStorage.setItem('analysisData', JSON.stringify(data));
            sessionStorage.setItem('videoId', JSON.stringify(videoId));

            // Create backend session and then set the dashboard URL (await so we always have sessionId)
            try {
                console.log('Creating session on backend...');
                const resp = await fetch(`${BACKEND_URL}/session`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ payload: data })
                });

                if (!resp.ok) {
                    console.warn('Session creation failed, status:', resp.status);
                    // fallback to old behaviour (no sid)
                    detailsLink.href = HOMEPAGE_URL + '/dashboard';
                } else {
                    const json = await resp.json();
                    const sessionId = json.session_id;
                    const dashboardUrl = `${HOMEPAGE_URL}/dashboard?sid=${sessionId}`;

                    // set href for visual / fallback usage
                    detailsLink.href = dashboardUrl;
                    console.log('Session created, dashboardUrl =', dashboardUrl);

                    // Set a single click handler that opens dashboard in a new tab (extension-friendly)
                    detailsLink.onclick = (e) => {
                        e.preventDefault();
                        // If extension API available, use chrome.tabs.create (more reliable)
                        if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.create) {
                            chrome.tabs.create({ url: dashboardUrl }, (tab) => {
                                console.log('Opened dashboard tab:', tab);
                            });
                        } else {
                            // fallback: open in new window/tab
                            window.open(dashboardUrl, '_blank');
                        }
                        return false;
                    };
                }
            } catch (e) {
                console.error('Failed to create session on backend:', e);
                detailsLink.href = HOMEPAGE_URL + '/dashboard';
                // still ensure click opens something
                detailsLink.onclick = (ev) => { ev.preventDefault(); window.open(detailsLink.href, '_blank'); return false; };
            }
        } else {
            detailsLink.href = BACKEND_URL; // fallback
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
