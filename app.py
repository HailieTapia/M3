from flask import Flask, render_template, request
import pandas as pd
import pickle

# Cargar el modelo de reglas
try:
    with open('reglas_asociacion.pkl', 'rb') as file:
        reglas = pickle.load(file, encoding='latin1')  # Para compatibilidad
    # Verificar si el DataFrame tiene las columnas necesarias
    if not all(col in reglas.columns for col in ['antecedents', 'consequents']):
        raise ValueError("El archivo pickle no tiene la estructura esperada")
except Exception as e:
    print(f"Error cargando pickle: {e}")
    reglas = pd.DataFrame(columns=['antecedents', 'consequents'])  # DataFrame vacío como fallback

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    recomendaciones = []
    productos_ingresados = []
    mensaje_error = None

    if request.method == 'POST':
        productos_input = request.form.get('productos', '')
        productos_ingresados = [p.strip().lower() for p in productos_input.split(',') if p.strip()]
        
        # Solo procesar si hay productos ingresados
        if productos_ingresados and not reglas.empty:
            try:
                # Buscar reglas que coincidan con los productos ingresados
                for _, fila in reglas.iterrows():
                    antecedente = list(fila['antecedents'])
                    consecuente = list(fila['consequents'])

                    if all(item in productos_ingresados for item in antecedente):
                        recomendaciones.extend(consecuente)

                # Eliminar duplicados y productos ya ingresados
                recomendaciones = list(set(recomendaciones) - set(productos_ingresados))
            except Exception as e:
                mensaje_error = f"Error procesando las reglas: {str(e)}"

    return render_template(
        'index.html',
        recomendaciones=recomendaciones,
        productos=productos_ingresados,
        error=mensaje_error
    )

if __name__ == '__main__':
    app.run(debug=True)