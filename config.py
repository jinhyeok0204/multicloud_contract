import os

class Config:
    SECRET_KEY = 'supersecretkey'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///users.db'
    UPLOAD_FOLDER = './uploads'
