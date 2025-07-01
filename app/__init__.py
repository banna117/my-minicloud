from flask import Flask

def create_app():
    app = Flask(__name__)

    from .routes.resource import resource_bp
    app.register_blueprint(resource_bp, url_prefix='/resources')

    return app