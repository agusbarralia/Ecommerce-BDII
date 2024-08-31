class User:
    def __init__(self, db):
        self.collection = db['users']

    def create_user(self, user_data):
        return self.collection.insert_one(user_data)

    def get_user(self, user_id):
        return self.collection.find_one({"userId": user_id})
# ver usuarios donde almacenamos 