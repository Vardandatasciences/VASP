from flask import Flask
from config.config import Config
import mysql.connector.pooling

def create_app():
    app = Flask(__name__, template_folder="templates")


    app.config.from_object(Config)
    
    # Initialize database pool
    app.db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="mypool",
        pool_size=5,
        pool_reset_session=True,
        **app.config['DB_CONFIG']
    )
    
    # Register blueprints
    from app.auth.routes import auth_bp
    from app.core.routes import core_bp
    from app.document_processing.routes import doc_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(core_bp)
    app.register_blueprint(doc_bp)

        
    return app