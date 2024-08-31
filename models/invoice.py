from datetime import datetime
from bson import ObjectId
from utils.redis_client import get_redis_client

class Invoice:
    def __init__(self, db):
        self.db = db
        self.collection = db['invoices']
        self.redis_client = get_redis_client()

    def get_next_invoice_number(self):
        # Incrementar el contador en Redis
        return self.redis_client.incr('invoice_number')
    
    def create_invoice(self, invoice_info):
        result = self.collection.insert_one(invoice_info)
        return str(result.inserted_id)

    def get_invoice_by_orderId(self, order_number):
        return self.collection.find_one({"order_number": int(order_number)})
