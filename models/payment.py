class Payment:
    def __init__(self, db):
        self.db = db

    def insert_payment(self, payment_info):
        self.db.payments.insert_one(payment_info)
