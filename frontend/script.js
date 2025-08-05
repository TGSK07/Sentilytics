document.getElementById('analyze-form').addEventListener('submit', async function (event) {
    event.preventDefault();

    const urlInput = document.getElementById('youtube-url');
    const errorEl = document.getElementById('url-error');
    const button = document.getElementById('analyze-button');
    const url = urlInput.value;

    const regex = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
    const match = url.match(regex);

    if (match && match[1]) {
        const videoId = match[1];
        errorEl.classList.add('hidden');
        button.disabled = true;
        button.textContent = 'Analyzing...';

        try {
            const apiUrl = `https://sentilyticsbackend-production.up.railway.app/dashboard/${videoId}`;
            const response = await fetch(apiUrl);

            if (!response.ok) {
                throw new Error(`API returned status ${response.status}`);
            }

            const data = await response.json();

            // Store the videoId and the data in session storage
            sessionStorage.setItem('analysisData', JSON.stringify(data));
            sessionStorage.setItem('videoId', videoId);

            // Redirect to the dashboard
            window.location.href = `dashboard.html`;

        } catch (error) {
            console.error('API call failed:', error);
            errorEl.textContent = 'Failed to analyze video. Please check the URL and try again.';
            errorEl.classList.remove('hidden');
            button.disabled = false;
            button.textContent = 'Analyze';
        }

    } else {
        errorEl.textContent = 'Please enter a valid YouTube video URL.';
        errorEl.classList.remove('hidden');
    }
});







document.addEventListener('DOMContentLoaded', function () {
    function updateDashboard(data, videoId) {
        document.getElementById('video-id').textContent = videoId;

        // Update summary cards
        document.getElementById('total-comments').textContent = data.totalComments.toLocaleString();
        document.getElementById('positive-comments').textContent = data.sentimentCounts.positive.toLocaleString();
        document.getElementById('negative-comments').textContent = data.sentimentCounts.negative.toLocaleString();
        document.getElementById('neutral-comments').textContent = data.sentimentCounts.neutral.toLocaleString();

        // Update chart images
        updateImage('sentiment-pie-chart', data.graph_urls.pie_chart);
        updateImage('likes-bar-chart', data.graph_urls.bar_chart);
        updateImage('word-cloud', data.graph_urls.word_cloud);

        // Update top comments - Note the change from 'text' to 'comment' in the response
        updateComment('top-liked-comment', data.top_liked_comments.positive[0]); // Assuming top liked is top positive
        updateComment('top-positive-comment', data.top_liked_comments.positive[0]);
        updateComment('top-negative-comment', data.top_liked_comments.negative[0]);
        updateComment('top-neutral-comment', data.top_liked_comments.neutral[0]);

        // Update insight lists
        updateList('questions-list', data.insight.Questions);
        updateList('suggestions-list', data.insight.Suggestions);
    }

    function updateImage(containerId, src) {
        const container = document.getElementById(containerId);
        const img = container.querySelector('img');
        const placeholder = container.querySelector('.placeholder-text');
        if (src) {
            img.src = src;
            img.onload = () => {
                img.classList.remove('hidden');
                if (placeholder) placeholder.classList.add('hidden');
            };
            img.onerror = () => {
                if (placeholder) placeholder.textContent = "Chart could not be loaded.";
            }
        } else {
            if (placeholder) placeholder.textContent = "Chart not available.";
        }
    }

    function updateComment(baseId, commentData) {
        const textEl = document.getElementById(`${baseId}-text`);
        const likesEl = document.getElementById(`${baseId}-likes`);
        if (commentData && commentData.comment) { // Changed from .text to .comment
            textEl.textContent = commentData.comment;
            likesEl.textContent = `👍 ${commentData.likecount.toLocaleString()} Likes`;
        } else {
            textEl.textContent = "No comment found for this category.";
            likesEl.textContent = "";
        }
    }

    function updateList(listId, items) {
        const listEl = document.getElementById(listId);
        listEl.innerHTML = '';
        if (items && items.length > 0) {
            items.forEach(item => {
                const li = document.createElement('li');
                li.textContent = item;
                listEl.appendChild(li);
            });
        } else {
            listEl.innerHTML = '<li>No items found.</li>';
        }
    }

    function showErrorMessage() {
        document.getElementById('dashboard-grid').classList.add('hidden');
        document.getElementById('error-message').classList.remove('hidden');
    }

    // --- Load data from session storage ---
    const analysisDataString = sessionStorage.getItem('analysisData');
    const videoId = sessionStorage.getItem('videoId');

    if (analysisDataString && videoId) {
        try {
            const analysisData = JSON.parse(analysisDataString);
            updateDashboard(analysisData, videoId);
        } catch (error) {
            console.error("Failed to parse analysis data from session storage:", error);
            showErrorMessage();
        }
    } else {
        showErrorMessage();
    }
});