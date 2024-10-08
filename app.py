from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

# Application, DB 초기화

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "secretkey"

db = SQLAlchemy(app)
migrate = Migrate(app, db)


from auth.routes import auth_bp
from main.routes import main_bp
from credentials.routes import credentials_bp
from deploy.routes import deploy_bp

app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(credentials_bp)
app.register_blueprint(deploy_bp)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
