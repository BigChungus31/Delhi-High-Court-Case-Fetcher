import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import os
import tempfile
import logging
from urllib.parse import urljoin, urlparse
import json
import random
import re

logger = logging.getLogger(__name__)

class CourtScraper:
    def __init__(self):
        self.base_url = "https://delhihighcourt.nic.in/"
        self.search_url = "https://delhihighcourt.nic.in/app/case-number"
        self.case_types_url = "https://delhihighcourt.nic.in/app/get-case-type-status"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def _get_driver(self):
        """Initialize Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--disable-ml-model-loading')
        chrome_options.add_argument('--disable-component-extensions-with-background-pages')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=TensorFlow')
        chrome_options.add_argument('--disable-ml-apis')
        chrome_options.add_argument('--disable-machine-learning-apis')
        chrome_options.add_argument('--disable-background-timer-throttling')
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {str(e)}")
            raise Exception("Chrome WebDriver initialization failed")
    
    def _random_delay(self, min_seconds=1, max_seconds=3):
        """Add random delay to mimic human behavior"""
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def get_dynamic_case_types(self, driver):
        """Scrape case types from the actual form dropdown"""
        try:
            # Try multiple possible dropdown names
            dropdown_names = ['case_type', 'ctype', 'type', 'casetype']
            for name in dropdown_names:
                try:
                    dropdown = driver.find_element(By.NAME, name)
                    options = dropdown.find_elements(By.TAG_NAME, "option")
                    case_types = [opt.get_attribute("value") for opt in options if opt.get_attribute("value")]
                    if case_types:
                        logger.info(f"Found {len(case_types)} case types from dropdown")
                        return case_types
                except NoSuchElementException:
                    continue
            
            # If no dropdown found, return hardcoded list
            logger.warning("No case type dropdown found, using hardcoded list")
            return self.get_supported_case_types()
            
        except Exception as e:
            logger.error(f"Error getting dynamic case types: {str(e)}")
            return self.get_supported_case_types()
    
    def search_case(self, case_type, case_number, filing_year, captcha=""):
        """
        Search for case information on Delhi High Court website
        
        Args:
            case_type (str): Type of case (WP, CRL, CS, etc.)
            case_number (str): Case number
            filing_year (str): Year of filing
            captcha (str): CAPTCHA value if required
            
        Returns:
            dict: Search result with success status and data/error
        """
        driver = None
        try:
            driver = self._get_driver()
            
            logger.info(f"Searching case: {case_type}/{case_number}/{filing_year}")
            
            # Parse case format like W.P.(C)/11199/2025
            if '/' in case_type and case_type.count('/') >= 2:
                parts = case_type.split('/')
                actual_case_type = parts[0]  # W.P.(C)
                actual_case_number = parts[1]  # 11199
                actual_filing_year = parts[2]  # 2025
            else:
                actual_case_type = case_type
                actual_case_number = case_number
                actual_filing_year = filing_year
            
            logger.info(f"Parsed - Type: {actual_case_type}, Number: {actual_case_number}, Year: {actual_filing_year}")

            # Test if website is accessible
            try:
                test_response = requests.get(self.search_url, timeout=10)
                logger.info(f"Website accessibility test: {test_response.status_code}")
            except Exception as e:
                logger.error(f"Website not accessible: {str(e)}")
            
            # Navigate to the search page
            logger.info("Navigating to search page...")
            driver.get(self.search_url)
            self._random_delay(2, 4)
            
            # Debug: Print page info
            logger.info(f"Page title: {driver.title}")
            logger.info(f"Current URL: {driver.current_url}")
            
            # Wait for the page to load
            wait = WebDriverWait(driver, 15)
            
            try:
                # Try form filling approach only
                return self._fill_form_and_search(driver, wait, actual_case_type, actual_case_number, actual_filing_year, captcha)
            except Exception as form_error:
                logger.error(f"Form filling failed: {str(form_error)}")
                return {
                    'success': False,
                    'error': f'Form submission failed: {str(form_error)}'
                }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in search_case: {error_msg}")
            return {
                'success': False,
                'error': f'Search failed: {error_msg}'
            }
        finally:
            if driver:
                driver.quit()
    
    def _fill_form_and_search(self, driver, wait, case_type, case_number, filing_year, captcha):
        """Fill form and submit search"""
        logger.info("Attempting form filling approach...")
        
        try:
            # Wait for and find case type dropdown
            case_type_field = wait.until(
                EC.element_to_be_clickable((By.NAME, 'case_type'))
            )
            from selenium.webdriver.support.ui import Select
            select = Select(case_type_field)
            
            # Dynamic case type mapping
            actual_case_type_value = case_type
            try:
                # First try exact match
                select.select_by_value(case_type)
                logger.info(f"Exact match found for case type: {case_type}")
            except:
                # If exact match fails, try to find matching option
                options = select.options
                found = False
                for option in options:
                    option_text = option.text.strip()
                    option_value = option.get_attribute('value')
                    
                    # Try multiple matching strategies
                    if (case_type in option_text or 
                        case_type in option_value or 
                        option_text in case_type or
                        case_type.replace('(', '').replace(')', '') in option_text):
                        select.select_by_value(option_value)
                        actual_case_type_value = option_value
                        logger.info(f"Mapped '{case_type}' to '{option_value}' ({option_text})")
                        found = True
                        break
                
                if not found:
                    raise Exception(f"Case type '{case_type}' not found in dropdown options")
            
            # Enter case number
            case_number_field = wait.until(
                EC.element_to_be_clickable((By.NAME, 'case_number'))
            )
            case_number_field.clear()
            case_number_field.send_keys(case_number)
            logger.info(f"Filled case number: {case_number}")
            
            # Select year
            year_field = wait.until(
                EC.element_to_be_clickable((By.NAME, 'year'))
            )
            year_select = Select(year_field)
            year_select.select_by_value(filing_year)
            logger.info(f"Selected year: {filing_year}")
            
            # Handle CAPTCHA (auto-read and fill)
            captcha_handled = self._handle_captcha(driver, None)  # No need to pass captcha
            if not captcha_handled['success']:
                return captcha_handled
            
            # Submit the form
            submit_button = self._find_submit_button(driver)
            if submit_button:
                logger.info("Submitting form...")
                submit_button.click()
                
                # Wait for results
                self._random_delay(3, 5)
                return self._parse_case_results(driver)
            else:
                raise Exception("Submit button not found")
                
        except Exception as e:
            logger.error(f"Form filling error: {str(e)}")
            raise e
    
    def _handle_captcha(self, driver, captcha):
        """Handle CAPTCHA by reading it from span element"""
        try:
            # Look for CAPTCHA span element
            try:
                captcha_span = driver.find_element(By.ID, "captcha-code")
                captcha_value = captcha_span.text.strip()
                logger.info(f"Found CAPTCHA value: {captcha_value}")
            except NoSuchElementException:
                return {
                    'success': False,
                    'error': 'CAPTCHA span element not found'
                }
            
            if not captcha_value or len(captcha_value) != 4 or not captcha_value.isdigit():
                return {
                    'success': False,
                    'error': f'Invalid CAPTCHA format: {captcha_value}'
                }
            
            # Find CAPTCHA input field
            captcha_field_selectors = [
                "//input[@name='captcha']",
                "//input[contains(@placeholder, 'captcha')]",
                "//input[contains(@id, 'captcha')]",
                "//input[@type='text']"
            ]
            
            captcha_field = None
            for selector in captcha_field_selectors:
                try:
                    captcha_field = driver.find_element(By.XPATH, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not captcha_field:
                return {
                    'success': False,
                    'error': 'CAPTCHA input field not found'
                }
            
            # Fill the CAPTCHA automatically
            captcha_field.clear()
            captcha_field.send_keys(captcha_value)
            logger.info(f"CAPTCHA auto-filled: {captcha_value}")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"CAPTCHA handling error: {str(e)}")
            return {
                'success': False,
                'error': f'CAPTCHA handling failed: {str(e)}'
            }
    
    def _find_submit_button(self, driver):
        """Find submit button using multiple strategies"""
        button_selectors = [
            "//button[@id='search']",
            "//input[@type='submit']",
            "//button[@type='submit']",
            "//input[@name='submit']",
            "//button[contains(text(), 'Search')]",
            "//button[contains(text(), 'Submit')]",
            "//input[@value='Search']"
        ]
        
        for selector in button_selectors:
            try:
                button = driver.find_element(By.XPATH, selector)
                if button.is_displayed() and button.is_enabled():
                    return button
            except NoSuchElementException:
                continue
        
        return None
    
    def _parse_case_results(self, driver):
        """Parse case search results from the page using multiple strategies"""
        try:
            logger.info("Parsing case results...")
            
            # Get page source and parse with BeautifulSoup
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Try multiple parsing strategies
            parsing_strategies = [
                self._parse_table_structure,
                self._parse_div_structure,
                self._parse_json_data,
                self._alternative_parsing
            ]
            
            for strategy in parsing_strategies:
                try:
                    result = strategy(soup)
                    if result['success']:
                        logger.info(f"Parsing successful with strategy: {strategy.__name__}")
                        return result
                except Exception as e:
                    logger.warning(f"Strategy {strategy.__name__} failed: {str(e)}")
                    continue
            
            # If all strategies fail, check for common error messages
            return self._check_for_errors(soup)
                
        except Exception as e:
            logger.error(f"Error parsing case results: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to parse case results: {str(e)}'
            }
    
    def _parse_table_structure(self, soup):
        """Parse case information from table structure"""
        case_data = {
            'parties': 'Not available',
            'filing_date': 'Not available',
            'hearing_date': 'Not available',
            'pdf_links': []
        }
        
        # Find tables containing case information
        tables = soup.find_all('table')
        
        # Find tables containing case information
        tables = soup.find_all('table')
        if not tables:
            return {'success': False, 'error': 'No tables found'}

        # Get all rows from all tables
        rows = []
        for table in tables:
            rows.extend(table.find_all('tr'))

        # First, find the header row to identify column positions
        headers = []
        header_row = None
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if cells and any('case no' in cell.get_text(strip=True).lower() for cell in cells):
                headers = [cell.get_text(strip=True).lower() for cell in cells]
                header_row = row
                break

        # If we found headers, parse data rows
        if headers:
            case_no_idx = party_idx = date_idx = -1
            for i, header in enumerate(headers):
                if 'case no' in header:
                    case_no_idx = i
                elif 'party' in header:
                    party_idx = i
                elif 'date' in header and ('judgment' in header or 'order' in header):
                    date_idx = i
            
            # Parse data rows
            for row in rows:
                if row == header_row:
                    continue
                cells = row.find_all(['td', 'th'])
                if len(cells) >= max(case_no_idx, party_idx, date_idx) + 1:
                    if party_idx >= 0 and party_idx < len(cells):
                        case_data['parties'] = cells[party_idx].get_text(strip=True)
                    if date_idx >= 0 and date_idx < len(cells):
                        case_data['filing_date'] = cells[date_idx].get_text(strip=True)
        else:
            # Fallback to original logic
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)
                    
                    if 'parties' in key or 'petitioner' in key or 'plaintiff' in key or 'vs' in key:
                        case_data['parties'] = value
                    elif 'filing' in key and 'date' in key:
                        case_data['filing_date'] = value
                    elif 'hearing' in key or 'next' in key:
                        case_data['hearing_date'] = value
        
        # Look for PDF links
        pdf_links = self._extract_pdf_links(soup)
        case_data['pdf_links'] = pdf_links
        
        # Check if we found meaningful data
        if (case_data['parties'] != 'Not available' or 
            case_data['filing_date'] != 'Not available' or 
            len(pdf_links) > 0):
            return {
                'success': True,
                'data': case_data
            }
        
        return {'success': False, 'error': 'No data found in table structure'}
    
    def _parse_div_structure(self, soup):
        """Parse case information from div/span structure"""
        case_data = {
            'parties': 'Not available',
            'filing_date': 'Not available',
            'hearing_date': 'Not available',
            'pdf_links': []
        }
        
        # Look for divs with class names that might contain case info
        info_divs = soup.find_all(['div', 'span'], class_=re.compile(r'case|info|detail|party', re.I))
        
        for div in info_divs:
            text = div.get_text(strip=True)
            if 'vs' in text.lower() or 'versus' in text.lower():
                case_data['parties'] = text
            elif 'filed' in text.lower() or 'filing' in text.lower():
                date_match = re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}', text)
                if date_match:
                    case_data['filing_date'] = date_match.group()
        
        # Look for PDF links
        pdf_links = self._extract_pdf_links(soup)
        case_data['pdf_links'] = pdf_links
        
        if case_data['parties'] != 'Not available' or len(pdf_links) > 0:
            return {
                'success': True,
                'data': case_data
            }
        
        return {'success': False, 'error': 'No data found in div structure'}
    
    def _parse_json_data(self, soup):
        """Parse case information from embedded JSON data"""
        try:
            # Look for script tags with JSON data
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and ('case' in script.string.lower() or 'data' in script.string.lower()):
                    # Try to extract JSON
                    json_match = re.search(r'\{.*\}', script.string)
                    if json_match:
                        try:
                            data = json.loads(json_match.group())
                            # Process JSON data if it contains case information
                            if isinstance(data, dict) and any(key in data for key in ['case', 'parties', 'filing']):
                                case_data = {
                                    'parties': data.get('parties', 'Not available'),
                                    'filing_date': data.get('filing_date', 'Not available'),
                                    'hearing_date': data.get('hearing_date', 'Not available'),
                                    'pdf_links': data.get('pdf_links', [])
                                }
                                return {
                                    'success': True,
                                    'data': case_data
                                }
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.warning(f"JSON parsing failed: {str(e)}")
        
        return {'success': False, 'error': 'No JSON data found'}
    
    def _extract_pdf_links(self, soup):
        """Extract PDF links from the page"""
        pdf_links = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href']
            if href.lower().endswith('.pdf') or 'pdf' in href.lower():
                pdf_url = urljoin(self.base_url, href)
                pdf_links.append({
                    'url': pdf_url,
                    'text': link.get_text(strip=True) or 'Download PDF'
                })
        
        return pdf_links
    
    def _check_for_errors(self, soup):
        """Check for common error messages"""
        error_messages = [
            'not found', 'no record', 'invalid', 'error', 'not available',
            'no case found', 'no data', 'please try again'
        ]
        
        page_text = soup.get_text().lower()
        for error_msg in error_messages:
            if error_msg in page_text:
                return {
                    'success': False,
                    'error': f'Court website returned: {error_msg}'
                }
        
        return {
            'success': False,
            'error': 'No case information found on the page'
        }
    
    def _alternative_parsing(self, soup):
        """Alternative parsing method for different page structures"""
        try:
            case_data = {
                'parties': 'Not available',
                'filing_date': 'Not available',
                'hearing_date': 'Not available',
                'pdf_links': []
            }
            
            # Look for any text that might contain case information
            all_text = soup.get_text()
            
            # Simple pattern matching for common case information
            lines = all_text.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:  # Skip very short lines
                    line_lower = line.lower()
                    
                    if 'vs' in line_lower or 'versus' in line_lower:
                        case_data['parties'] = line
                    elif any(date_word in line_lower for date_word in ['filed', 'filing', 'date']):
                        # Look for date patterns
                        date_pattern = r'\d{1,2}[-/]\d{1,2}[-/]\d{4}'
                        dates = re.findall(date_pattern, line)
                        if dates:
                            case_data['filing_date'] = dates[0]
            
            # Look for PDF links
            pdf_links = self._extract_pdf_links(soup)
            case_data['pdf_links'] = pdf_links
            
            # If we found some basic information, return success
            if case_data['parties'] != 'Not available' or len(pdf_links) > 0:
                return {
                    'success': True,
                    'data': case_data
                }
            else:
                return {
                    'success': False,
                    'error': 'No case information found'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Alternative parsing failed: {str(e)}'
            }
    
    def download_pdf(self, pdf_url):
        """Download PDF file and return temporary file path with validation"""
        try:
            # Validate PDF first
            logger.info(f"Validating PDF URL: {pdf_url}")
            head_response = self.session.head(pdf_url, timeout=10)
            
            if head_response.status_code != 200:
                logger.error(f"PDF URL returned {head_response.status_code}")
                return None
                
            content_type = head_response.headers.get('content-type', '')
            if 'pdf' not in content_type.lower() and 'application/octet-stream' not in content_type.lower():
                logger.error(f"URL doesn't return PDF: {content_type}")
                return None
            
            # Download the PDF
            logger.info("Downloading PDF...")
            response = self.session.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file.write(response.content)
            temp_file.close()
            
            logger.info(f"PDF downloaded successfully: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error downloading PDF from {pdf_url}: {str(e)}")
            return None
    
    def get_supported_case_types(self):
        """Get list of supported case types for the selected court"""
        return [
            'WP',      # Writ Petition
            'CRL',     # Criminal
            'CS',      # Civil Suit
            'FAO',     # First Appeal from Order
            'CRL.A',   # Criminal Appeal
            'CRL.REV', # Criminal Revision
            'CM',      # Civil Miscellaneous
            'W.P.(C)', # Writ Petition (Civil)
            'CRL.M.C', # Criminal Misc Case
            'BAIL'     # Bail Application
        ]