from flask import Flask, render_template, request
import pandas as pd
import pickle

# Cargar el modelo de reglas
with open('reglas_asociacion.pkl', 'rb') as file:
    reglas = pickle.load(file)

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    recomendaciones = []
    productos_ingresados = []

    if request.method == 'POST':
        productos_ingresados = request.form.get('productos')
        productos_ingresados = [p.strip().lower() for p in productos_ingresados.split(',')]

        # Buscar reglas que coincidan con los productos ingresados
        for _, fila in reglas.iterrows():
            antecedente = list(fila['antecedents'])
            consecuente = list(fila['consequents'])

            if all(item in productos_ingresados for item in antecedente):
                recomendaciones.extend(consecuente)

        # Eliminar duplicados y productos ya ingresados
        recomendaciones = list(set(recomendaciones) - set(productos_ingresados))

    return render_template('index.html', recomendaciones=recomendaciones, productos=productos_ingresados)

if __name__ == '__main__':
    app.run(debug=True)
