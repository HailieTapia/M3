from flask import Flask, request, jsonify
import joblib
import pandas as pd
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

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
    Endpoint para obtener recomendaciones de productos basadas en el carrito
    Recibe: {'cart': ['Producto1', 'Producto2', ...]}
    Devuelve: {'cart': List[str], 'recommendations': List[str], 'count': int, 'success': bool}
    """
    try:
        # Obtener los productos del carrito
        request_data = request.get_json()
        if not request_data or 'cart' not in request_data:
            app.logger.warning("Solicitud sin datos o sin campo 'cart'")
            return jsonify({
                'success': False,
                'error': "El campo 'cart' es requerido",
                'recommendations': []
            }), 400
        
        cart = request_data['cart']
        if not isinstance(cart, list):
            app.logger.warning("El campo 'cart' debe ser una lista")
            return jsonify({
                'success': False,
                'error': "El campo 'cart' debe ser una lista de productos",
                'recommendations': []
            }), 400
        
        app.logger.info(f"Solicitud de recomendación para el carrito: {cart}")
        
        # Verificar si el modelo está cargado
        if rules is None or rules.empty:
            app.logger.error("Intento de uso con modelo no cargado")
            return jsonify({
                'success': False,
                'error': "El sistema de recomendación no está disponible",
                'recommendations': []
            }), 503
        
        # Convertir el carrito en un conjunto para comparación
        cart_set = set(cart)
        
        # Buscar reglas donde los antecedentes sean un subconjunto del carrito
        matching_rules = rules[rules['antecedents'].apply(lambda x: x.issubset(cart_set))]
        app.logger.info(f"Reglas encontradas para el carrito: {len(matching_rules)}")
        
        if matching_rules.empty:
            app.logger.info(f"No se encontraron reglas para el carrito: {cart}")
            return jsonify({
                'success': True,
                'cart': cart,
                'recommendations': [],
                'count': 0,
                'message': f"No se encontraron recomendaciones para el carrito {cart}"
            })
        
        # Filtrar reglas por confianza y lift para obtener recomendaciones más relevantes
        matching_rules = matching_rules[matching_rules['confidence'] >= 0.5]
        matching_rules = matching_rules[matching_rules['lift'] > 1.2]
        
        # Obtener recomendaciones y limpiar resultados
        recommendations = matching_rules['consequents'].tolist()
        flat_recommendations = list({item for sublist in recommendations for item in sublist if item not in cart_set})
        
        app.logger.info(f"Recomendaciones generadas para el carrito {cart}: {flat_recommendations}")
        
        return jsonify({
            'success': True,
            'cart': cart,
            'recommendations': flat_recommendations,
            'count': len(flat_recommendations),
            'rules_used': len(matching_rules)
        })
    
    except Exception as e:
        app.logger.error(f"Error en la generación de recomendaciones: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': "Error interno al procesar la solicitud",
            'recommendations': []
        }), 500

if __name__ == '__main__':
    app.logger.info("Iniciando la aplicación Flask")
    app.run(host='0.0.0.0', port=5000)