# 데이터베이스 모델 정의. 사용자의 정보를 저장하고 관리하는 역할
# User : 사용자 모델(자격 증명 정보 포함)

from app import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    credentials = db.relationship('Credential', backref='user', lazy=True)
    deployments = db.relationship('Deployment', backref='user', lazy=True)
    encryption_key = db.Column(db.String(150), nullable=False) # 사용자별 암호화 키

    def __repr__(self):
        return f'<User {self.username}>'


class Credential(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    csp = db.Column(db.String(10), nullable=False)
    credential_data = db.Column(db.LargeBinary, nullable=False)
    description = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f'<Credential {self.csp}>'


class Deployment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    details = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

