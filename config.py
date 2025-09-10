import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost/tenfingers')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'supersecretkey')
    DEBUG = os.environ.get('FLASK_DEBUG', '').lower() in {'1', 'true', 't', 'yes'}
