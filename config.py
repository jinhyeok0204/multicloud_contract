import os


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'supersecretkey')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///users.db')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', './uploads')
