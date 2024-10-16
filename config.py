import os
from dotenv import load_dotenv

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER')
