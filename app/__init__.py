from flask import Flask
from flask_login import LoginManager

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this'
app.config['WTF_CSRF_ENABLED'] = False

login_manager = LoginManager(app)
login_manager.login_view = 'index'

from app import routes