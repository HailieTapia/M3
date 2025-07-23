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
    product = request.form['product']
    recommendations = rules[rules['antecedents'].apply(lambda x: product in x)]['consequents'].tolist()
    # Convertir a una lista plana y eliminar duplicados
    flat_recommendations = list(set([item for sublist in recommendations for item in sublist]))
    return render_template('index.html', recommendations=flat_recommendations, product=product)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)