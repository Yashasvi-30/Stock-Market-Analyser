import os
import yfinance as yf
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_cors import CORS
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from extensions import db, bcrypt, login_manager
from utils.news import  news
from utils.portfolio import load_portfolio, add_stock, remove_stock, get_portfolio
from utils.analysis import analyze_sentiment, perform_risk_analysis
from models.portfolio import Portfolio
from models.user import User
from models.stock import Stock
from datetime import datetime
import requests

API_KEY = '2SU4SFQ9OYTZZMJ1'
API_BASE_URL = 'https://www.alphavantage.co/query'



def fetch_stock_data(symbol):
    # Fetch real-time price
    price_params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": API_KEY
    }
    price_resp = requests.get(API_BASE_URL, params=price_params)
    price_data = price_resp.json()

    price = "N/A"
    if "Global Quote" in price_data and price_data["Global Quote"].get("05. price"):
        try:
            price = round(float(price_data["Global Quote"]["05. price"]), 2)
        except:
            pass

    # Fetch sector and market cap
    overview_params = {
        "function": "OVERVIEW",
        "symbol": symbol,
        "apikey": API_KEY
    }
    overview_resp = requests.get(API_BASE_URL, params=overview_params)
    overview_data = overview_resp.json()

    sector = overview_data.get("Sector", "N/A")
    market_cap = overview_data.get("MarketCapitalization", "N/A")
    if market_cap != "N/A":
        try:
            market_cap = f"{int(market_cap) // 1_00_00_000} Cr"  # Convert to Crores
        except:
            market_cap = "N/A"

    return {"price": price, "sector": sector, "market_cap": market_cap}

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
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet (Google)",
    "AMZN": "Amazon",
    "TSLA": "Tesla",
    
      }

    # 🔑 Twelve Data API key
    TD_API_KEY = 'd128a9e96d7c4442af79d360dacc2257'

    # 📊 Fetch real-time quote data from Twelve Data API
    famous_stocks = []
    for symbol, name in famous_tickers.items():
        try:
            response = requests.get(
                "https://api.twelvedata.com/quote",
                params={"symbol": symbol, "apikey": TD_API_KEY},
                timeout=10  # avoid hanging if API is slow
            )
            data = response.json()

            # Check for API error
            if "price" not in data:
                raise Exception(f"Twelve Data error: {data.get('message')}")

            stock_info = {
                "name": name,
                "details": {
                    "Price": data.get("price", "N/A"),
                    "High": data.get("high", "N/A"),
                    "Low": data.get("low", "N/A")
                }
            }
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            # In case of failure, add placeholder values
            stock_info = {
                "name": name,
                "details": {
                    "Price": "N/A",
                    "High": "N/A",
                    "Low": "N/A"
                }
            }
        # Append to the final list
        famous_stocks.append(stock_info)

    # Fetch current stock-related news
    news_articles = fetch_stock_news()

    # Chart Data
    stock_labels = [stock.company_name for stock in portfolio_data]
    stock_shares = [stock.shares for stock in portfolio_data]

    # Sector and Exchange Data
    from collections import Counter
    sector_counts = Counter(stock.sector for stock in portfolio_data)
    sector_labels = list(sector_counts.keys())
    sector_values = list(sector_counts.values())
    exchange_labels = ['NSE', 'BSE']
    exchange_values = [0, 0]

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
        exchange_labels=exchange_labels,
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

##Stock time series html 

# Twelve Data API Key
TD_API_KEY = 'd128a9e96d7c4442af79d360dacc2257'

# Fetch stock time series data
def fetch_time_series_dataabc(symbolabc):
    url = f'https://api.twelvedata.com/time_series?symbol={symbolabc}&interval=1day&outputsize=30&apikey={TD_API_KEY}'
    response = requests.get(url)
    data = response.json()

    if "values" in data:
        return data["values"]
    else:
        print("API Error:", data.get("message"))
        return None

# Route to handle form input and display
@app.route("/stockscreenerabc", methods=["GET", "POST"])
def stock_screenerabc():
    if request.method == "POST":
        stock_symbolabc = request.form.get("symbolabc")
        if stock_symbolabc:
            return redirect(url_for("show_stock_dataabc", symbolabc=stock_symbolabc.upper()))
        else:
            flash("Please enter a stock symbol.")
            return redirect(url_for("stock_screenerabc"))
    return render_template("stock_time_series.html")

# Route to show stock data
@app.route("/stockabc/<symbolabc>")
def show_stock_dataabc(symbolabc):
    time_series_dataabc = fetch_time_series_dataabc(symbolabc)
    if time_series_dataabc:
        return render_template("stock_time_series.html", symbolabc=symbolabc, time_series_dataabc=time_series_dataabc)
    else:
        flash(f"No data found for symbol: {symbolabc}")
        return redirect(url_for("stock_screenerabc"))



# Create DB + Run App
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Ensure that the database is created
    app.run(debug=True)