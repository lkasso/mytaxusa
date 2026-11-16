"""Public home and welcome pages."""
from flask import render_template

def register_routes(app):
    @app.get('/')
    def home():
        return render_template('home.html')

    @app.get('/welcome')
    def welcome():
        return render_template('welcome.html')

