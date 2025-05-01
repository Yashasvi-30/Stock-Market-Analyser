import pandas as pd
import numpy as np
import re
import nltk
import pickle
from nltk.corpus import stopwords
from sklearn.model_selection import train_test_split
from sklearn.utils import class_weight
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping

nltk.download('stopwords')

# Load dataset
df = pd.read_csv("data/Twitter_Data.csv")
print("Columns in dataset:", df.columns)

# Standardize column names
if 'text' in df.columns:
    df.rename(columns={'text': 'clean_text'}, inplace=True)

# Convert columns to string type
df['clean_text'] = df['clean_text'].astype(str)
df['category'] = df['category'].astype(str)

# Show original unique categories
print("Original unique category values:", df['category'].unique())

# --- ADD THIS --- #
# Negation Handling Function
def handle_negation(text):
    negation_pattern = r'\b(not|no|never)\s+(\w+)\b'
    modified_text = re.sub(negation_pattern, r'\1_\2', text)
    return modified_text

# Clean text function
def clean_text(text):
    text = text.lower()
    text = handle_negation(text)  # Handle negations first!
    text = re.sub(r"http\S+|@\w+|#\w+|[^a-zA-Z\s]", '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    tokens = text.split()
    tokens = [word for word in tokens if word not in stopwords.words('english')]
    return ' '.join(tokens)

# ----------------- #

# Apply cleaning
df['clean_text'] = df['clean_text'].apply(clean_text)

# Map numeric sentiment values to classes
label_map = {
    '-1.0': 0,  # Negative
    '0.0': 1,   # Neutral
    '1.0': 2    # Positive
}
df = df[df['category'].isin(label_map.keys())]
df['category'] = df['category'].map(label_map)

# Final category check
print("Unique categories after mapping:", df['category'].unique())
print("Category counts:\n", df['category'].value_counts())

# Drop rows with missing values
df.dropna(subset=['clean_text', 'category'], inplace=True)

# Tokenization
tokenizer = Tokenizer(num_words=10000, oov_token='<OOV>')
tokenizer.fit_on_texts(df['clean_text'])
sequences = tokenizer.texts_to_sequences(df['clean_text'])
X = pad_sequences(sequences, maxlen=100)
y = df['category'].astype(int).values

# Check target values
if len(y) == 0:
    raise ValueError("y is empty. Check your dataset and category mapping.")

# Compute class weights
classes = np.unique(y)
weights = class_weight.compute_class_weight(class_weight='balanced', classes=classes, y=y)
class_weights = dict(zip(classes, weights))
print("Class weights:", class_weights)

# Train-test split
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

# Build LSTM model
model = Sequential([
    Embedding(input_dim=10000, output_dim=128, input_length=100),
    LSTM(64),
    Dropout(0.5),
    Dense(3, activation='softmax')
])
model.compile(loss='sparse_categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

# Train model
early_stop = EarlyStopping(monitor='val_loss', patience=3)
history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=10,
    batch_size=32,
    class_weight=class_weights,
    callbacks=[early_stop],
    verbose=2
)

# Save model and tokenizer
model.save("lstm_sentiment_model.keras")
with open("tokenizer.pkl", "wb") as f:
    pickle.dump(tokenizer, f)

print("✅ LSTM model trained and saved successfully.")
