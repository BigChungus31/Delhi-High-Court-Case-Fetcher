import sqlite3
import json
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path='court_data.db'):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def initialize_database(self):
        """Create database tables if they don't exist"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create queries table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS queries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        case_type TEXT NOT NULL,
                        case_number TEXT NOT NULL,
                        filing_year TEXT NOT NULL,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        status TEXT NOT NULL DEFAULT 'pending',
                        error_message TEXT
                    )
                ''')
                
                # Create case_data table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS case_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query_id INTEGER NOT NULL,
                        parties TEXT,
                        filing_date TEXT,
                        hearing_date TEXT,
                        pdf_links TEXT,
                        raw_response TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (query_id) REFERENCES queries (id)
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_queries_timestamp 
                    ON queries(timestamp)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_queries_status 
                    ON queries(status)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_case_data_query_id 
                    ON case_data(query_id)
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            raise
    
    def store_query(self, case_type, case_number, filing_year, status='pending', error_message=None):
        """
        Store a new query in the database
        
        Returns:
            int: The ID of the inserted query
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO queries (case_type, case_number, filing_year, status, error_message)
                    VALUES (?, ?, ?, ?, ?)
                ''', (case_type, case_number, filing_year, status, error_message))
                
                query_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Stored query with ID: {query_id}")
                return query_id
                
        except Exception as e:
            logger.error(f"Error storing query: {str(e)}")
            raise
    
    def update_query_status(self, query_id, status, error_message=None):
        """Update the status of a query"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE queries 
                    SET status = ?, error_message = ?
                    WHERE id = ?
                ''', (status, error_message, query_id))
                
                conn.commit()
                logger.info(f"Updated query {query_id} status to: {status}")
                
        except Exception as e:
            logger.error(f"Error updating query status: {str(e)}")
            raise
    
    def store_case_data(self, query_id, parties, filing_date, hearing_date, pdf_links, raw_response):
        """Store case data results"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Convert pdf_links to JSON string if it's a list
                if isinstance(pdf_links, list):
                    pdf_links_json = json.dumps(pdf_links)
                else:
                    pdf_links_json = pdf_links
                
                cursor.execute('''
                    INSERT INTO case_data 
                    (query_id, parties, filing_date, hearing_date, pdf_links, raw_response)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (query_id, parties, filing_date, hearing_date, pdf_links_json, raw_response))
                
                case_data_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Stored case data with ID: {case_data_id}")
                return case_data_id
                
        except Exception as e:
            logger.error(f"Error storing case data: {str(e)}")
            raise
    
    def get_query_by_id(self, query_id):
        """Get query details by ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT q.*, cd.parties, cd.filing_date, cd.hearing_date, 
                           cd.pdf_links, cd.raw_response
                    FROM queries q
                    LEFT JOIN case_data cd ON q.id = cd.query_id
                    WHERE q.id = ?
                ''', (query_id,))
                
                result = cursor.fetchone()
                
                if result:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, result))
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching query by ID: {str(e)}")
            return None
    
    def get_recent_queries(self, limit=50):
        """Get recent queries with their results"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT q.id, q.case_type, q.case_number, q.filing_year,
                           q.timestamp, q.status, q.error_message,
                           cd.parties, cd.filing_date, cd.hearing_date, cd.pdf_links
                    FROM queries q
                    LEFT JOIN case_data cd ON q.id = cd.query_id
                    ORDER BY q.timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                results = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                queries = []
                for result in results:
                    query_dict = dict(zip(columns, result))
                    
                    # Parse PDF links if they exist
                    if query_dict['pdf_links']:
                        try:
                            query_dict['pdf_links'] = json.loads(query_dict['pdf_links'])
                        except json.JSONDecodeError:
                            query_dict['pdf_links'] = []
                    else:
                        query_dict['pdf_links'] = []
                    
                    queries.append(query_dict)
                
                return queries
                
        except Exception as e:
            logger.error(f"Error fetching recent queries: {str(e)}")
            return []
    
    def get_statistics(self):
        """Get database statistics"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total queries
                cursor.execute('SELECT COUNT(*) FROM queries')
                total_queries = cursor.fetchone()[0]
                
                # Successful queries
                cursor.execute("SELECT COUNT(*) FROM queries WHERE status = 'completed'")
                successful_queries = cursor.fetchone()[0]
                
                # Failed queries
                cursor.execute("SELECT COUNT(*) FROM queries WHERE status = 'failed'")
                failed_queries = cursor.fetchone()[0]
                
                # Queries by case type
                cursor.execute('''
                    SELECT case_type, COUNT(*) as count 
                    FROM queries 
                    GROUP BY case_type 
                    ORDER BY count DESC
                ''')
                case_type_stats = cursor.fetchall()
                
                # Recent activity (last 24 hours)
                cursor.execute('''
                    SELECT COUNT(*) FROM queries 
                    WHERE timestamp >= datetime('now', '-1 day')
                ''')
                recent_activity = cursor.fetchone()[0]
                
                return {
                    'total_queries': total_queries,
                    'successful_queries': successful_queries,
                    'failed_queries': failed_queries,
                    'success_rate': (successful_queries / total_queries * 100) if total_queries > 0 else 0,
                    'case_type_distribution': dict(case_type_stats),
                    'recent_activity_24h': recent_activity
                }
                
        except Exception as e:
            logger.error(f"Error fetching statistics: {str(e)}")
            return {
                'total_queries': 0,
                'successful_queries': 0,
                'failed_queries': 0,
                'success_rate': 0,
                'case_type_distribution': {},
                'recent_activity_24h': 0
            }
    
    def cleanup_old_data(self, days=30):
        """Clean up old data older than specified days"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete old case data first (due to foreign key constraint)
                cursor.execute('''
                    DELETE FROM case_data 
                    WHERE query_id IN (
                        SELECT id FROM queries 
                        WHERE timestamp < datetime('now', '-' || ? || ' days')
                    )
                ''', (days,))
                
                deleted_case_data = cursor.rowcount
                
                # Delete old queries
                cursor.execute('''
                    DELETE FROM queries 
                    WHERE timestamp < datetime('now', '-' || ? || ' days')
                ''', (days,))
                
                deleted_queries = cursor.rowcount
                
                conn.commit()
                
                logger.info(f"Cleaned up {deleted_queries} queries and {deleted_case_data} case data records older than {days} days")
                
                return {
                    'deleted_queries': deleted_queries,
                    'deleted_case_data': deleted_case_data
                }
                
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return {
                'deleted_queries': 0,
                'deleted_case_data': 0
            }