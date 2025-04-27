from datetime import datetime
from extensions import db  # ✅ correct

from models.user import User  # if using user_id for foreign key

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_symbol = db.Column(db.String(20), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    sector = db.Column(db.String(50))
    shares = db.Column(db.Float, nullable=False)
    avg_cost = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, default=0.0)
    from datetime import date
    purchase_date = db.Column(db.Date, nullable=False)

    exchange = db.Column(db.String(10))
    user = db.relationship("User", backref=db.backref("stocks", lazy=True))
    def __repr__(self):
        return f'<Stock {self.stock_symbol} ({self.shares} shares)>'
