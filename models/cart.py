from bson import ObjectId

class Cart:
    def __init__(self, db):
        self.collection = db['carts']

    def create_cart(self, cart_data):
        return self.collection.insert_one(cart_data)

    def get_cart(self, cart_id):
        cart = self.collection.find_one({"cartId": cart_id})
        if cart:
           
           # Convertir ObjectId a string
            for item in cart.get("items", []):
                item["productId"] = str(item["productId"])
            return cart.get("items", [])
        else:
            
            # Devolver una lista vacía si no existe
            return []

    def update_cart(self, cart_id, update_data):
        return self.collection.update_one({"cartId": cart_id}, {"$set": update_data}, upsert=True)

    def delete_cart(self, cart_id):
        return self.collection.delete_one({"cartId": cart_id})

    def add_to_cart(self, cart_id, product_id, quantity, product_name):
        items = self.get_cart(cart_id)
        for item in items:
            if item["productId"] == product_id:
                item["quantity"] += quantity
                break
        else:
            items.append({"productId": product_id, "quantity": quantity, "name": product_name})
        self.update_cart(cart_id, {"items": items})

    def remove_from_cart(self, cart_id, product_id):
        items = self.get_cart(cart_id)
        items = [item for item in items if item["productId"] != product_id]
        self.update_cart(cart_id, {"items": items})

    def update_cart_quantity(self, cart_id, product_id, quantity):
        items = self.get_cart(cart_id)
        for item in items:
            if item["productId"] == product_id:
                item["quantity"] = quantity
                break
        self.update_cart(cart_id, {"items": items})
