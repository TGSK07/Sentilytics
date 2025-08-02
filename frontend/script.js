async function loadDashboard() {
    const videoId = "exampleVideoId"; // replace dynamically as needed
    const response = await fetch(`/dashboard/${videoId}`);
    const data = await response.json();

    // Set sentiment stats
    const total = data.totalComments;
    document.getElementById("positive").innerText = `${((data.sentimentCounts.positive/total)*100).toFixed(1)}%`;
    document.getElementById("neutral").innerText = `${((data.sentimentCounts.neutral/total)*100).toFixed(1)}%`;
    document.getElementById("negative").innerText = `${((data.sentimentCounts.negative/total)*100).toFixed(1)}%`;

    // Set charts
    document.getElementById("pieChart").src = data.graph_urls.pie_chart;
    document.getElementById("wordCloud").src = data.graph_urls.word_cloud;
    document.getElementById("barChart").src = data.graph_urls.bar_chart;

    // Populate questions
    const qList = document.getElementById("questionsList");
    qList.innerHTML = data.insight.Questions.map(q => `<li>${q}</li>`).join("");

    // Populate suggestions
    const sList = document.getElementById("suggestionsList");
    sList.innerHTML = data.insight.Suggestions.map(s => `<li>${s}</li>`).join("");

    // Populate top liked comments
    const cList = document.getElementById("commentsList");
    cList.innerHTML = "";
    for (let sentiment in data.top_liked_comments) {
        data.top_liked_comments[sentiment].forEach(comment => {
            const div = document.createElement("div");
            div.classList.add("comment");
            div.innerHTML = `<strong>${sentiment.toUpperCase()}</strong>: ${comment.comment}<span>Likes: ${comment.likecount}</span>`;
            cList.appendChild(div);
        });
    }
}

loadDashboard();
