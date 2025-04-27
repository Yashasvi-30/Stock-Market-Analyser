import os
import yfinance as yf
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from extensions import db, bcrypt, login_manager
from utils.news import fetch_stock_news
from utils.portfolio import load_portfolio, add_stock, remove_stock, get_portfolio
from utils.analysis import analyze_sentiment, perform_risk_analysis
from models.portfolio import Portfolio
from models.user import User
from models.stock import Stock
from datetime import datetime
import requests


# App Initialization
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance/users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "supersecretkey"

# Initialize extensions
CORS(app)
db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "auth"
login_manager.login_message_category = "info"

# Load user
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home / Landing page
@app.route("/")
def home():
    return render_template("index.html")

# Authentication: Sign In / Sign Up
@app.route("/signin", methods=["GET", "POST"])
@app.route("/signup", methods=["GET", "POST"])
def auth():
    if request.method == "POST":
        form_type = request.form.get("form_type")
        if form_type == "signup":
            username = request.form.get("username")
            email = request.form.get("email")
            password = request.form.get("password")
            confirm = request.form.get("confirm")

            if password != confirm:
                flash("Passwords do not match.")
                return redirect(url_for('auth'))

            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(username=username, email=email, password=hashed_pw)

            try:
                db.session.add(new_user)
                db.session.commit()
                flash("Sign Up successful! You can now log in.")
                return redirect(url_for('auth'))
            except:
                flash("User already exists or error saving user.")
                return redirect(url_for('auth'))

        elif form_type == "signin":
            username = request.form.get("username")
            password = request.form.get("password")

            user = User.query.filter_by(username=username).first()
            if user and bcrypt.check_password_hash(user.password, password):
                login_user(user)  # ✅ LOGIN THE USER
                flash("Login successful!")

                # ✅ Redirect to next page or dashboard
                next_page = request.args.get("next")
                return redirect(next_page) if next_page else redirect(url_for("dashboard"))
            else:
                flash("Invalid username or password.")
                return redirect(url_for('auth'))

    return render_template("auth.html")

# Dashboard Page
@app.route("/dashboard")
@login_required
def dashboard():
    user_id = current_user.id
    portfolio_data = Stock.query.filter_by(user_id=user_id).all()

    total_stocks = len(portfolio_data)
    total_shares = sum(stock.shares for stock in portfolio_data)
    total_value = sum(stock.shares * stock.avg_cost for stock in portfolio_data)
    total_profit = round(total_value * 0.1, 2)  # Example 10% profit
   

    famous_tickers = {
        "RELIANCE.NS": "Reliance",
        "TCS.NS": "TCS",
        "HDFCBANK.NS": "HDFC Bank",
        "SBIN.NS": "SBI",
        "INFY.NS": "Infosys"
    }

    famous_stocks = []
    for ticker, name in famous_tickers.items():
        data = yf.download(ticker, period="1d", progress=False)
        price = round(data["Close"].iloc[-1], 2) if not data.empty else "N/A"
        famous_stocks.append({"name": name, "price": price})

    # Fetch current stock-related news
    news_articles = fetch_stock_news()

 
    # Chart Data
    stock_labels = [stock.company_name for stock in portfolio_data]
    stock_shares = [stock.shares for stock in portfolio_data]

    from collections import Counter
    sector_counts = Counter(stock.sector for stock in portfolio_data)
    sector_labels = list(sector_counts.keys())
    sector_values = list(sector_counts.values())
    exchange_labels = ['NSE', 'BSE']  # Example exchange labels
    exchange_values = [0, 0]  # Example counts for exchanges

    for stock in portfolio_data:
        if stock.exchange == 'NSE':
            exchange_values[0] += 1
        elif stock.exchange == 'BSE':
            exchange_values[1] += 1

    return render_template(
        "dashboard.html",
        current_user=current_user,
        total_stocks=total_stocks,
        total_shares=total_shares,
        total_value=round(total_value, 2),
        total_profit=total_profit,
        portfolio_data=portfolio_data,
        famous_stocks=famous_stocks,
        news_articles=news_articles,
        stock_labels=stock_labels,
        stock_shares=stock_shares,
        sector_labels=sector_labels,
        sector_values=sector_values,
        exchange_labels=exchange_labels,  # Pass the exchange labels
        exchange_values=exchange_values
    
    )

# API Endpoints
@app.route("/api/portfolio")
def api_get_portfolio():
    return jsonify(get_portfolio())

@app.route("/api/add", methods=["POST"])
def api_add():
    data = request.get_json()
    add_stock(data["ticker"], data["name"], float(data["shares"]), float(data["price"]))
    return jsonify({"status": "success"})

@app.route("/api/remove/<ticker>", methods=["DELETE"])
def api_remove(ticker):
    remove_stock(ticker)
    return jsonify({"status": "removed"})

@app.route("/api/sentiment", methods=["POST"])
def api_sentiment():
    data = request.get_json()
    return jsonify(analyze_sentiment(data["text"]))

@app.route("/api/risk")
def api_risk():
    return jsonify(perform_risk_analysis())

# Add Stock Route
@app.route("/add_stock", methods=["GET", "POST"])
@login_required
def add_stock_route():
    if request.method == "POST":
        ticker = request.form.get("ticker")
        name = request.form.get("name")
        shares = float(request.form.get("shares"))
        price = float(request.form.get("price"))

        new_entry = Portfolio(
            user_id=current_user.id,
            ticker=ticker,
            name=name,
            shares=shares,
            price_per_share=price
        )
        db.session.add(new_entry)
        db.session.commit()
        flash("Stock added to your portfolio.")
        return redirect(url_for("dashboard"))

    return render_template("add_stock.html")

# Portfolio Management
@app.route('/portfolio', methods=['GET', 'POST'])
@login_required
def portfolio():
    if request.method == 'POST':
        try:
            symbol = request.form['symbol'].upper()
            company_name = request.form['company_name']
            sector = request.form['sector']
            shares = float(request.form['shares'])
            avg_cost = float(request.form['avg_cost'])
            purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date()
            # Data for Pie Chart
            

            exchange = request.form['exchange']
            
            new_stock = Stock(
                user_id=current_user.id,
                stock_symbol=symbol,
                company_name=company_name,
                sector=sector,
                shares=shares,
                avg_cost=avg_cost,
                purchase_date=purchase_date,
                exchange=exchange
            )
            db.session.add(new_stock)
            db.session.commit()
            flash('Stock added successfully!', 'success')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

    stocks = Stock.query.filter_by(user_id=current_user.id).all()
    return render_template('portfolio.html', stocks=stocks)

@app.route('/edit_stock/<int:stock_id>', methods=['POST'])
@login_required
def edit_stock(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    if stock.user_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("portfolio"))

    try:
        stock.company_name = request.form["company_name"]
        stock.sector = request.form["sector"]
        stock.shares = float(request.form["shares"])
        stock.avg_cost = float(request.form["avg_cost"])
        stock.purchase_date = datetime.strptime(request.form["purchase_date"], '%Y-%m-%d').date()
        stock.exchange = request.form["exchange"]
        db.session.commit()
        flash("Stock updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating stock: {str(e)}", "danger")

    return redirect(url_for("portfolio"))
@app.route('/delete_stock/<int:stock_id>', methods=['POST'])
@login_required
def delete_stock(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    if stock.user_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("portfolio"))

    db.session.delete(stock)
    db.session.commit()
    flash("Stock deleted successfully!", "success")
    return redirect(url_for("portfolio"))
@app.route('/smart-insights')
def smart_insights():
    return render_template('smart_insights.html')

@app.route('/quiz')
def quiz():
    return render_template('quiz.html')  

# Alpha Vantage API key and base URL
API_KEY = '2SU4SFQ9OYTZZMJ1'
API_BASE_URL = 'https://www.alphavantage.co/query'


# Function to get stock data
def get_stock_data(symbol):
    """Fetches daily stock data using Alpha Vantage API."""
    params = {
        'function': 'TIME_SERIES_DAILY',
        'symbol': symbol,
        'apikey': API_KEY
    }
    response = requests.get(API_BASE_URL, params=params)
    data = response.json()

    if 'Time Series (Daily)' in data:
        stock_data = data['Time Series (Daily)']
        return stock_data
    else:
        return None

from flask import Flask, request, jsonify, render_template
import tensorflow as tf
import pickle
from tensorflow.keras.preprocessing.sequence import pad_sequences

# Load your model and tokenizer
model = tf.keras.models.load_model('lstm_sentiment_model.keras')
tokenizer = pickle.load(open('tokenizer.pkl', 'rb'))

@app.route('/market_sentiment', methods=["GET", "POST"])
@login_required
def market_sentiment():
    sentiment = None
    if request.method == "POST":
        message = request.form.get("message")
        sentiment = analyze_sentiment(message)  # Assuming you have a function to analyze sentiment
    return render_template('market_sentiment.html', sentiment=sentiment)
@app.route('/predict-market-sentiment', methods=['POST'])
def predict_market_sentiment():
    data = request.get_json()
    message = data['message']
    
    # Tokenize and process the message as per your model's requirements
    sequence = tokenizer.texts_to_sequences([message])
    padded = pad_sequences(sequence, maxlen=100)
    
    # Predict sentiment using the model
    prediction = model.predict(padded)
    sentiment = ['Negative', 'Neutral', 'Positive'][prediction.argmax()]
    
    return jsonify({'sentiment': sentiment})


# Create DB + Run App
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Ensure that the database is created
    app.run(debug=True)