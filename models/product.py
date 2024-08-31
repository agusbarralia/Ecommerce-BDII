from bson import ObjectId

class Product:
    def __init__(self, db):
        self.collection = db['products']

    def add_product(self, product_data):
        return self.collection.insert_one(product_data)

    def get_product(self, product_id):
        return self.collection.find_one({"productId": product_id})

    def update_product(self, product_id, update_data):
        return self.collection.update_one({"productId": product_id}, {"$set": update_data})

    def delete_product(self, product_id):
        return self.collection.update_one(
            {"productId": product_id},
            {"$set": {"isDeleted": True, "stock": 0}}
        )
    
    def get_all_products(self):
        return list(self.collection.find())
    
    def get_active_products(self):
        return list(self.collection.find({"isDeleted": False, "stock": {"$gt": 0}}))
    
    def get_active_products_admin(self):
        return list(self.collection.find({"isDeleted": False}))

    def get_deleted_products(self):
        return list(self.collection.find({"isDeleted": True}))

    def decrement_stock(self, product_id, quantity):
        return self.collection.update_one(
            {"productId": product_id, "isDeleted": False, "stock": {"$gt": quantity - 1}},
            {"$inc": {"stock": -quantity}}
        )