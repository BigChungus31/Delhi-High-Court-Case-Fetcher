# Indian Courts Case Fetcher

A comprehensive web scraping application for fetching case information from Indian courts, specifically designed for the **Delhi High Court** website. The application provides automated case lookup, CAPTCHA handling, and data persistence with a user-friendly web interface.

## Supported Court

**Delhi High Court** - `https://delhihighcourt.nic.in/`
- Case search and information retrieval
- PDF document downloads
- Multiple case type support

## Features

- **Automated Case Search**: Search cases by type, number, and filing year
- **Smart CAPTCHA Handling**: Automatic CAPTCHA reading from span elements
- **Multiple Case Types**: Support for WP, CRL, CS, FAO, and more
- **PDF Downloads**: Direct download of case-related documents
- **Data Persistence**: SQLite database for search history and results
- **Web Interface**: Clean, responsive UI with modern design and form validation
- **REST API**: JSON API endpoints for programmatic access
- **Error Handling**: Comprehensive error logging and user feedback
- **Multiple Parsing Strategies**: Robust data extraction from various page layouts
- **Responsive Design**: Mobile-friendly interface with professional styling

## Quick Start

### Prerequisites

- Python 3.8+
- Google Chrome browser
- ChromeDriver (auto-managed via webdriver-manager)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd indian-courts-fetcher
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env file with your configurations
   ```

5. **Initialize Database**
   ```bash
   python initialise.py
   ```

6. **Run the Application**
   ```bash
   python app.py
   ```

7. **Access the Application**
   - Web Interface: `http://localhost:5000`
   - API Endpoints: `http://localhost:5000/api/`

## Configuration

### Environment Variables (.env)

```bash
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your_secret_key_here

# Database Configuration
DATABASE_PATH=court_data.db

# Scraping Configuration
SCRAPING_DELAY=2
MAX_RETRIES=3
REQUEST_TIMEOUT=30

# Chrome WebDriver Configuration
CHROME_EXECUTABLE_PATH=/usr/bin/google-chrome
CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# Rate Limiting
REQUESTS_PER_MINUTE=10
REQUESTS_PER_HOUR=100

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=court_fetcher.log

# Security Settings
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000

# Court Website Configuration
COURT_BASE_URL=https://delhihighcourt.nic.in/
COURT_SEARCH_URL=https://delhihighcourt.nic.in/app/case-number

# PDF Download Settings
PDF_DOWNLOAD_TIMEOUT=60
MAX_PDF_SIZE_MB=50

# Cleanup Settings
CLEANUP_DAYS=30
AUTO_CLEANUP=True
```

## CAPTCHA Strategy

The application employs an **intelligent CAPTCHA handling system**:

### Automatic CAPTCHA Reading
- **Source**: Reads CAPTCHA values from `<span id="captcha-code">` elements
- **Validation**: Ensures 4-digit numeric format
- **Auto-fill**: Automatically populates CAPTCHA input fields
- **Error Handling**: Graceful fallback for invalid/missing CAPTCHAs

### Implementation Details
```python
def _handle_captcha(self, driver, captcha):
    # Locate CAPTCHA span element
    captcha_span = driver.find_element(By.ID, "captcha-code")
    captcha_value = captcha_span.text.strip()
    
    # Validate format (4-digit numeric)
    if len(captcha_value) == 4 and captcha_value.isdigit():
        # Auto-fill CAPTCHA field
        captcha_field.send_keys(captcha_value)
```

## Supported Case Types

The application supports various case types from Delhi High Court:

- **WP** - Writ Petition
- **W.P.(C)** - Writ Petition (Civil)
- **CRL** - Criminal Cases
- **CRL.A** - Criminal Appeal
- **CRL.REV** - Criminal Revision
- **CRL.M.C** - Criminal Miscellaneous Case
- **CS** - Civil Suit
- **FAO** - First Appeal from Order
- **CM** - Civil Miscellaneous
- **BAIL** - Bail Application

## API Endpoints

### Search Case
```http
POST /api/search
Content-Type: application/json

{
  "case_type": "W.P.(C)",
  "case_number": "11199",
  "filing_year": "2025",
  "captcha": "1234"
}
```

### Download PDF
```http
GET /api/download/<pdf_url>
```

### Search History
```http
GET /api/history
```

### Health Check
```http
GET /health
```

## Database Schema

### Queries Table
```sql
CREATE TABLE queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_type TEXT NOT NULL,
    case_number TEXT NOT NULL,
    filing_year TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT
);
```

### Case Data Table
```sql
CREATE TABLE case_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER NOT NULL,
    parties TEXT,
    filing_date TEXT,
    hearing_date TEXT,
    pdf_links TEXT,
    raw_response TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_id) REFERENCES queries (id)
);
```

## Technical Architecture

### Core Components

1. **Flask Application** (`app.py`)
   - REST API endpoints
   - Request handling and validation
   - Error management

2. **Web Scraper** (`scraper.py`)
   - Selenium WebDriver automation
   - Multiple parsing strategies
   - CAPTCHA handling
   - PDF downloads

3. **Database Manager** (`database.py`)
   - SQLite operations
   - Query logging
   - Data persistence
   - Statistics tracking

### Parsing Strategies

The scraper employs multiple parsing strategies for robust data extraction:

1. **Table Structure Parsing** - Extracts data from HTML tables
2. **Div Structure Parsing** - Handles modern div-based layouts
3. **JSON Data Parsing** - Processes embedded JavaScript data
4. **Alternative Parsing** - Fallback text-based extraction

## Error Handling

### Common Error Scenarios

- **Invalid Case Types**: Automatic mapping and validation
- **CAPTCHA Failures**: Retry mechanism with error reporting
- **Network Timeouts**: Configurable timeout settings
- **Page Structure Changes**: Multiple parsing fallbacks
- **PDF Download Issues**: Validation and error handling

### Logging

Comprehensive logging system tracks:
- Search requests and responses
- CAPTCHA handling results
- Database operations
- Error conditions and stack traces

## Security Features

- **Rate Limiting**: Configurable request limits
- **Input Validation**: SQL injection prevention
- **CORS Configuration**: Controlled cross-origin access
- **Error Sanitization**: Sensitive information protection

## Performance Optimization

- **Connection Pooling**: Efficient database connections
- **Caching Strategy**: Temporary file management
- **Random Delays**: Human-like browsing behavior
- **Resource Cleanup**: Automatic browser instance cleanup

## Testing

### Manual Testing
1. Start the application
2. Navigate to `http://localhost:5000`
3. Enter case details:
   - Case Type: `W.P.(C)`
   - Case Number: `11199`
   - Filing Year: `2025`
4. Submit and verify results

### API Testing
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{"case_type":"W.P.(C)","case_number":"11199","filing_year":"2025"}'
```

## Troubleshooting

### Common Issues

1. **ChromeDriver Issues**
   ```bash
   # Update webdriver-manager
   pip install --upgrade webdriver-manager
   ```

2. **Database Lock Errors**
   ```bash
   # Remove database file and reinitialize
   rm court_data.db
   python initialise.py
   ```

3. **CAPTCHA Reading Failures**
   - Check if court website structure changed
   - Verify CAPTCHA span element exists
   - Enable debug logging for detailed information

4. **Network Connectivity**
   - Verify court website accessibility
   - Check firewall settings
   - Test with different network connections

## Development

### Adding New Courts

1. Create new scraper class inheriting from `CourtScraper`
2. Update `base_url` and `search_url`
3. Implement court-specific parsing methods
4. Add case type mappings

### Extending Functionality

1. **New Case Types**: Update `get_supported_case_types()`
2. **Additional Fields**: Modify database schema and parsing logic
3. **New Endpoints**: Add routes in `app.py`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request

## Support

For issues and questions:
1. Check troubleshooting section
2. Review logs in `court_fetcher.log`
3. Create GitHub issue with detailed information

---


**Note**: This application is designed for legitimate legal research purposes. Users are responsible for complying with website terms of service and applicable laws.
