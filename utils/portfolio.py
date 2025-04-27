import os

filename = "portfolio.txt"
portfolio = {}

def load_portfolio():
    global portfolio
    portfolio = {}
    if os.path.exists(filename):
        with open(filename) as f:
            for line in f:
                ticker, name, shares, price = line.strip().split(",")
                portfolio[ticker] = {
                    "name": name,
                    "shares": float(shares),
                    "price": float(price)
                }

def save_portfolio():
    with open(filename, "w") as f:
        for t, d in portfolio.items():
            f.write(f"{t},{d['name']},{d['shares']},{d['price']}\n")

def add_stock(ticker, name, shares, price):
    load_portfolio()
    portfolio[ticker] = {
        "name": name,
        "shares": float(shares),
        "price": float(price)
    }
    save_portfolio()

def remove_stock(ticker):
    load_portfolio()
    if ticker in portfolio:
        del portfolio[ticker]
        save_portfolio()

def get_portfolio():
    load_portfolio()
    return portfolio
