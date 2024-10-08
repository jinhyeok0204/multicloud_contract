# 데이터베이스 모델 정의. 사용자의 정보를 저장하고 관리하는 역할
# User : 사용자 모델(자격 증명 정보 포함)

from app import db

class Deployment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    details = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # 고유한 사용자 ID
    username = db.Column(db.String(150), unique=True, nullable=False)  # 사용자 이름 (고유)
    password = db.Column(db.String(150), nullable=False)  # 사용자 비밀번호 (해시된 형태로 저장)

    # AWS 자격 증명
    aws_access_key = db.Column(db.String(150))  # AWS Access Key ID
    aws_secret_key = db.Column(db.String(150))  # AWS Secret Access Key

    # GCP 자격 증명 (서비스 계정 JSON 파일 경로)
    gcp_credentials = db.Column(db.String(150))  # GCP 자격 증명 파일 경로

    # Azure 자격 증명 (Azure 서비스 원본 파일 경로)
    azure_credentials = db.Column(db.String(150))  # Azure 자격 증명 파일 경로

    def __repr__(self):
        return f'<User {self.username}>'
