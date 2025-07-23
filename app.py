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
    Endpoint para obtener recomendaciones de productos
    Recibe: {'product': 'Nombre del producto'}
    Devuelve: {'product': str, 'recommendations': List[str], 'count': int, 'success': bool}
    """
    try:
        # Obtener el producto del cuerpo de la solicitud
        request_data = request.get_json()
        if not request_data or 'product' not in request_data:
            app.logger.warning("Solicitud sin datos o sin campo 'product'")
            return jsonify({
                'success': False,
                'error': "El campo 'product' es requerido",
                'recommendations': []
            }), 400
        
        product = request_data['product']
        app.logger.info(f"Solicitud de recomendación para el producto: {product}")
        
        # Verificar si el modelo está cargado (forma correcta para DataFrames)
        if rules is None or rules.empty:  # Cambiado para manejar DataFrames correctamente
            app.logger.error("Intento de uso con modelo no cargado")
            return jsonify({
                'success': False,
                'error': "El sistema de recomendación no está disponible",
                'recommendations': []
            }), 503
        
        # Buscar reglas donde el producto está en los antecedentes
        matching_rules = rules[rules['antecedents'].apply(lambda x: product in x)]
        app.logger.info(f"Reglas encontradas que contienen el producto: {len(matching_rules)}")
        
        if matching_rules.empty:  # Cambiado para usar .empty en lugar de len()
            app.logger.info(f"No se encontraron reglas para el producto: {product}")
            return jsonify({
                'success': True,
                'product': product,
                'recommendations': [],
                'count': 0,
                'message': f"No se encontraron recomendaciones para {product}"
            })
        
        # Obtener recomendaciones y limpiar resultados
        recommendations = matching_rules['consequents'].tolist()
        flat_recommendations = list({item for sublist in recommendations for item in sublist})
        
        app.logger.info(f"Recomendaciones generadas para {product}: {flat_recommendations}")
        
        return jsonify({
            'success': True,
            'product': product,
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