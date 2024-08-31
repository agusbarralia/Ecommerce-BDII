from pymongo import MongoClient

def get_db():
    client = MongoClient("mongodb://127.0.0.1:27017/?directConnection=true&serverSelectionTimeoutMS=2000&appName=mongosh+2.2.3")
    db = client['TiendaMia_db']
    return db
