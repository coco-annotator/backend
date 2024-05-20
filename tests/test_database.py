from pymongo import MongoClient, ReplaceOne
from pymongo.errors import ServerSelectionTimeoutError



user_keys = ['_id', 'password', 'username', 'name', 'online', 'is_admin', 'preferences', 'permissions', 'last_seen']

def test_get_user_from_db():
    client = MongoClient('localhost', 27018)
    db = client['flask']
    collection = db['user_model']
    result = collection.find_one({"username": "Admin"})
    assert result is not None


if __name__ == '__main__':
    test_get_user_from_db()