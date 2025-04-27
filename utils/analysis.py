from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def analyze_sentiment(text):
    analyzer = SentimentIntensityAnalyzer()
    score = analyzer.polarity_scores(text)
    score["sentiment"] = "Positive" if score["compound"] >= 0.05 else "Negative" if score["compound"] <= -0.05 else "Neutral"
    return score

def perform_risk_analysis():
    return {
        "risk_score": 5.7,
        "beta": 1.15,
        "sharpe_ratio": 0.85,
        "diversification": 6.2,
        "concentration": "High"
    }
