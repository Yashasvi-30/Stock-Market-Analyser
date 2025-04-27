import pickle
import re
import nltk
import numpy as np
import tensorflow as tf
from nltk.corpus import stopwords
from tensorflow.keras.preprocessing.sequence import pad_sequences

nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

# Load model and tokenizer
model = tf.keras.models.load_model("model/lstm_model.h5")
with open("model/tokenizer.pkl", "rb") as f:
    tokenizer = pickle.load(f)

# Preprocessing
def preprocess(text):
    text = re.sub(r"http\S+|@\w+|#\w+|[^a-zA-Z\s]", '', text.lower())
    return ' '.join([word for word in text.split() if word not in stop_words])

def predict_sentiment(text):
    clean = preprocess(text)
    seq = tokenizer.texts_to_sequences([clean])
    padded = pad_sequences(seq, maxlen=100)
    pred = model.predict(padded)[0][0]
    return "Positive" if pred >= 0.5 else "Negative"

# Example
text_input = "I love using this app. It's amazing!"
print(f"Text: {text_input}")
print(f"Sentiment: {predict_sentiment(text_input)}")
