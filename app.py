from flask import Flask, render_template, request
import joblib
import pandas as pd

app = Flask(__name__)

# Cargar el modelo de reglas de asociación
rules = joblib.load('models/reglas_asociacion.pkl')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    # Obtener el producto ingresado por el usuario
    product = request.form['product']
    
    # Filtrar reglas que contengan el producto en los antecedentes
    recommendations = rules[rules['antecedents'].apply(lambda x: product in x)]['consequents'].tolist()
    recommendations = [list(rec) for rec in recommendations]
    
    return render_template('index.html', recommendations=recommendations, product=product)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)