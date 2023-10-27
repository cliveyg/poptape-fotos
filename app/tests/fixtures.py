# app/tests/fixtures.py

#from app import db
#from app.models import Foto
#import uuid
import datetime
import time

# users and roles for testing

# -----------------------------------------------------------------------------

def make_datetime_string():
    ts = time.time()
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

# -----------------------------------------------------------------------------

def login_body(**kwargs):

    if "name" and "passwd" in kwargs:
        return { 'username': kwargs['name'], 'password': kwargs['passwd'] }

    return { 'username': 'woody', 'password': 'password' }

# -----------------------------------------------------------------------------

def headers_with_token(token):

    headers = { 'Content-type': 'application/json',
                'x-access-token': token }
    return headers    

# -----------------------------------------------------------------------------

#def addTestFotos():


# -----------------------------------------------------------------------------

