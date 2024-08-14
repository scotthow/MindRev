from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
from mindrev.config import Config
from mindrev.settings import init_app as init_settings

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'users.login'
login_manager.login_message_category = 'info'
mail = Mail()

def create_tables(app):
    with app.app_context():
        db.create_all()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    init_settings(app)  # Call init_settings after creating the app

    from mindrev.users.routes import users
    from mindrev.game_creation.routes import game_creation_bp
    from mindrev.npc_chat.routes import npc_chat_bp
    from mindrev.main.routes import main
    app.register_blueprint(users)
    app.register_blueprint(game_creation_bp)
    app.register_blueprint(npc_chat_bp)
    app.register_blueprint(main)

    create_tables(app)  # Add this line to create tables

    return app