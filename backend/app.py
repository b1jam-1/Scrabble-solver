import os
from flask import Flask, render_template
try:
    from api import api_bp
except ImportError:
    from .api import api_bp

# Chemins pour le dossier frontend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'frontend'))

app = Flask(
    __name__,
    static_folder=os.path.join(FRONTEND_DIR, 'static'),
    template_folder=os.path.join(FRONTEND_DIR, 'templates')
)

@app.route('/')
def index():
    return render_template('index.html')

# Enregistrement du blueprint API
app.register_blueprint(api_bp, url_prefix='/api')