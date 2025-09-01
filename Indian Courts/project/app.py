from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import os
from datetime import datetime
import logging
from scraper import CourtScraper
from database import DatabaseManager
import traceback

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize components
db_manager = DatabaseManager()
court_scraper = CourtScraper()

@app.route('/')
def index():
    """Render the main form page"""
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search_case():
    """Handle case search requests"""
    try:
        data = request.get_json()
        
        # Validate input
        required_fields = ['case_type', 'case_number', 'filing_year']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        case_type = data['case_type']
        case_number = data['case_number']
        filing_year = data['filing_year']
        captcha = data.get('captcha', '')
        
        # Store query in database
        query_id = db_manager.store_query(
            case_type=case_type,
            case_number=case_number,
            filing_year=filing_year,
            status='processing'
        )
        
        logger.info(f"Processing case search: {case_type}/{case_number}/{filing_year}")
        logger.info(f"CAPTCHA provided: {'Yes' if captcha else 'No'}")

        # Perform scraping
        result = court_scraper.search_case(
            case_type=case_type,
            case_number=case_number,
            filing_year=filing_year,
            captcha=captcha
        )
        
        if result['success']:
            # Store successful result
            db_manager.store_case_data(
                query_id=query_id,
                parties=result['data']['parties'],
                filing_date=result['data']['filing_date'],
                hearing_date=result['data']['hearing_date'],
                pdf_links=result['data']['pdf_links'],
                raw_response=str(result['data'])
            )
            
            # Update query status
            db_manager.update_query_status(query_id, 'completed')
            
            return jsonify({
                'success': True,
                'data': result['data'],
                'query_id': query_id
            })
        else:
            # Store error
            db_manager.update_query_status(
                query_id, 
                'failed', 
                error_message=result['error']
            )
            
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400
            
    except Exception as e:
        logger.error(f"Error in search_case: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'Internal server error occurred'
        }), 500

@app.route('/api/download/<path:pdf_url>')
def download_pdf(pdf_url):
    """Proxy PDF downloads through the application"""
    try:
        pdf_file = court_scraper.download_pdf(pdf_url)
        if pdf_file:
            return send_file(
                pdf_file,
                as_attachment=True,
                download_name=f"case_document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mimetype='application/pdf'
            )
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to download PDF'
            }), 404
            
    except Exception as e:
        logger.error(f"Error downloading PDF: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to download PDF'
        }), 500

@app.route('/api/history')
def get_search_history():
    """Get recent search history"""
    try:
        history = db_manager.get_recent_queries(limit=50)
        return jsonify({
            'success': True,
            'data': history
        })
    except Exception as e:
        logger.error(f"Error fetching history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch search history'
        }), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    # Initialize database
    db_manager.initialize_database()
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)