from app.fake_passwords import FAKE_PASSWORDS
from random import randint
from passlib.apps import custom_app_context as password_context
from app.database import get_database
from bson.objectid import ObjectId
from pprint import pprint
from itsdangerous import TimedJSONWebSignatureSerializer as JSONSerializer
from itsdangerous import BadSignature, SignatureExpired
from config import SECRET_KEY
from json import loads
from app.mail import send_subscription_mail
from flask import render_template


def random_fake_password():
    max = len(FAKE_PASSWORDS) - 1
    return FAKE_PASSWORDS[randint(0, max)] + str(randint(0, 99))

class UserAlreadyExists(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

class User():

    # BSON or JSON deserialization, to check origin - see is_registered method
    def __init__(self, document):
        if "_id" in document:
            self._id = str(document["_id"])

        self.email = document["email"]

        if "password" in document:
            self.password = document["password"]

        self.first_name = document["first_name"]
        self.last_name = document["last_name"]
        self.rights = document["rights"]
        self.themes = document["themes"]
        if "hospital" in document:
            self.hospital = document["hospital"]
        
    def is_registered(self):
        return hasattr(self, "_id")

    def get_id(self):
        if hasattr(self, '_id'):
            return self._id

    @staticmethod
    def get(user_id):
        db = get_database()
        return User(db.users.find_one({'_id': ObjectId(user_id)}))

    @staticmethod
    def sanitize(user):
        sanitized_user = vars(user)
        del sanitized_user['_id']
        del sanitized_user['password']
        del sanitized_user['email']
        return sanitized_user

    def generate_auth_token(self):
        if not hasattr(self, '_id'):
            return None

        serializer = JSONSerializer(SECRET_KEY, expires_in=12*60*60)
        return serializer.dumps({'user_id': self._id})

    @staticmethod
    def verify_token(token):
        serializer = JSONSerializer(SECRET_KEY)
        try:
            data = serializer.loads(token)

        except SignatureExpired:
            return None


        user = User.get(data["user_id"])
        return user
        
    def register(self):
        if self.is_registered(): return None
        db = get_database()
        password = random_fake_password()
        self.password = password_context.hash(password)
        user = db.users.find_one({'email': self.email})
        if not user:
            print(render_template("subscribe.txt", user=self.email, password=password))
            # send_subscription_mail(self, password)
            res = db.users.insert_one(vars(self))
            return res.inserted_id
        else:
            raise UserAlreadyExists

    
    def check_password(self, password):
        if not hasattr(self, 'password'): 
            return False
        return password_context.verify(password, self.password)
    
