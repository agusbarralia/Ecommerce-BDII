from bson import ObjectId

class Order:
    def __init__(self, db):
        self.db = db

    def insert_order(self, order_info):
        self.db.orders.insert_one(order_info)

    def get_order(self, order_id):
        order = self.db.orders.find_one({"order_number": int(order_id)})
        return order

    def get_all_orders(self):
        return list(self.db.orders.find({}))

    def update_order_status(self, order_number, status):
        self.db.orders.update_one({"order_number": order_number}, {"$set": {"status": status}})


    def get_orders_by_user(self, user_id):
        return list(self.db.orders.find({"user_id": user_id}))
