from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import pandas as pd
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
CORS(app)  # Permitir solicitudes desde cualquier origen

# Configuración avanzada del logging
logging.basicConfig(level=logging.INFO)
handler = RotatingFileHandler('app.log', maxBytes=100000, backupCount=3)  # 100KB por archivo, 3 backups
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)

# Cargar el modelo de reglas de asociación
try:
    rules = joblib.load('models/reglas_asociacion.pkl')
    app.logger.info("Modelo de reglas de asociación cargado correctamente")
    app.logger.info(f"Número de reglas cargadas: {len(rules)}")
    
    # Log de ejemplo de las primeras reglas (solo en desarrollo)
    if app.debug:
        app.logger.debug("Ejemplo de reglas cargadas:")
        for i, rule in rules.head(3).iterrows():
            app.logger.debug(f"Regla {i}: {rule['antecedents']} => {rule['consequents']}")
            
except Exception as e:
    app.logger.error(f"Error al cargar el modelo: {str(e)}", exc_info=True)
    rules = None

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar el estado del servicio"""
    status = {
        'status': 'OK' if rules is not None else 'ERROR',
        'model_loaded': rules is not None,
        'rules_count': len(rules) if rules is not None else 0
    }
    return jsonify(status)

@app.route('/recommend', methods=['POST'])
def recommend():
    """
    Endpoint para obtener recomendaciones de productos basadas en un producto o carrito
    Recibe: {'product': str} o {'cart': List[str]}
    Devuelve: {'success': bool, 'input': str|List[str], 'recommendations': List[str], 'message': str}
    """
    try:
        # Obtener los datos del cuerpo de la solicitud
        request_data = request.get_json()
        if not request_data or ('product' not in request_data and 'cart' not in request_data):
            app.logger.warning("Solicitud sin datos o sin campo 'product' o 'cart'")
            return jsonify({
                'success': False,
                'error': "Se requiere el campo 'product' o 'cart'",
                'recommendations': [],
                'message': "Solicitud inválida"
            }), 400
        
        # Determinar si se envió un solo producto o un carrito
        if 'product' in request_data:
            input_data = [request_data['product']]  # Convertir producto en lista
            input_type = 'product'
        else:
            input_data = request_data['cart']
            input_type = 'cart'
        
        # Validar que input_data sea una lista válida
        if not isinstance(input_data, list) or not all(isinstance(p, str) for p in input_data):
            app.logger.warning(f"El campo '{input_type}' debe ser una lista de strings")
            return jsonify({
                'success': False,
                'error': f"El campo '{input_type}' debe ser una lista de productos",
                'recommendations': [],
                'message': "Formato de entrada inválido"
            }), 400
        
        app.logger.info(f"Solicitud de recomendación para {input_type}: {input_data}")
        
        # Verificar si el modelo está cargado
        if rules is None or rules.empty:
            app.logger.error("Intento de uso con modelo no cargado")
            return jsonify({
                'success': False,
                'error': "El sistema de recomendación no está disponible",
                'recommendations': [],
                'message': "Modelo no disponible"
            }), 503
        
        # Convertir los productos en un conjunto para comparación
        input_set = set(p.strip() for p in input_data)
        
        # Buscar reglas donde los antecedentes sean un subconjunto del input
        matching_rules = rules[rules['antecedents'].apply(lambda x: x.issubset(input_set))]
        app.logger.info(f"Reglas encontradas para {input_type} {input_data}: {len(matching_rules)}")
        
        # Obtener recomendaciones
        recommendations = set()
        for cons in matching_rules['consequents']:
            recommendations.update(set(c.strip() for c in cons if c.strip() not in input_set))
        
        # Si no hay recomendaciones, usar productos populares como respaldo
        if not recommendations:
            app.logger.info(f"No se encontraron recomendaciones para {input_type}: {input_data}")
            popular_products = ['Taza de Porcelana', 'USB Personalizado']  # Ajustar según datos reales
            recommendations = set(p for p in popular_products if p not in input_set)
            message = f"No se encontraron recomendaciones específicas para {input_type} {input_data}. Mostrando productos populares."
        else:
            message = f"Recomendaciones generadas para {input_type} {input_data}"
        
        app.logger.info(f"Recomendaciones generadas: {recommendations}")
        
        return jsonify({
            'success': True,
            'input': input_data,
            'recommendations': sorted(recommendations),
            'count': len(recommendations),
            'message': message
        })
    
    except Exception as e:
        app.logger.error(f"Error en la generación de recomendaciones: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': "Error interno al procesar la solicitud",
            'recommendations': [],
            'message': "Error en el servidor"
        }), 500

if __name__ == '__main__':
    app.logger.info("Iniciando la aplicación Flask")
    app.run(host='0.0.0.0', port=5000, debug=True)