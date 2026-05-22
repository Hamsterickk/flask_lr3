from datetime import datetime
from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id=0):
        self.id = id
        self.name = ""
        self.email = ""
        self.password = ""
        self.wallet = None
        self.review_text = ""
        self.review_rating = 0
        self.review_sent = False

    def get_id(self):
        return str(self.id)

    def create_wallet(self):
        self.wallet = Wallet(self.id)


class Wallet:
    def __init__(self, user_id=0):
        self.user_id = user_id
        self.balance = 0.0
        self.card_number = ""
        self.expiry_date = ""
        self.cvc = ""
        self.transactions = []

    def pay(self, amount, description):
        if self.balance >= amount:
            self.balance -= amount
            self.transactions.append({
                'date': datetime.now(),
                'amount': -amount,
                'description': description
            })
            return True
        return False
