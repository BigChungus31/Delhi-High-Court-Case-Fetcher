// Court Data Fetcher - Frontend JavaScript

class CourtDataFetcher {
    constructor() {
        this.apiBase = '/api';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.populateYearDropdown();
        document.getElementById('caseNumber').setAttribute('autocomplete', 'off');
    }

    setupEventListeners() {
        // Form submission
        const searchForm = document.getElementById('searchForm');
        searchForm.addEventListener('submit', (e) => this.handleSearch(e));

        // Form validation
        const inputs = searchForm.querySelectorAll('input, select');
        inputs.forEach(input => {
            input.addEventListener('change', () => this.validateForm());
        });
    }

    populateYearDropdown() {
        const yearSelect = document.getElementById('filingYear');
        const currentYear = new Date().getFullYear();
        
        // Add years from current year back to 2000 (all years available with scroll)
        for (let year = currentYear; year >= 2000; year--) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            yearSelect.appendChild(option);
        }
    }

    validateForm() {
        const caseType = document.getElementById('caseType').value;
        const caseNumber = document.getElementById('caseNumber').value;
        const filingYear = document.getElementById('filingYear').value;
        
        const isValid = caseType && caseNumber && filingYear;
        const submitBtn = document.getElementById('searchBtn');
        
        submitBtn.disabled = !isValid;
        return isValid;
    }

    async handleSearch(event) {
        event.preventDefault();
        
        if (!this.validateForm()) {
            this.showError('Please fill in all required fields');
            return;
        }

        const formData = new FormData(event.target);
        const searchData = {
            case_type: formData.get('case_type'),
            case_number: formData.get('case_number'),
            filing_year: formData.get('filing_year'),
            captcha: formData.get('captcha') || ''
        };

        this.setLoadingState(true);
        this.hideError();
        this.hideResults();

        try {
            const response = await fetch(`${this.apiBase}/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(searchData)
            });

            const result = await response.json();

            if (result.success) {
                this.displayResults(result.data);
            } else {
                this.showError(result.error || 'Search failed');
                
                // Show CAPTCHA field if needed
                if (result.error && result.error.toLowerCase().includes('captcha')) {
                    this.showCaptchaField();
                }
            }
        } catch (error) {
            console.error('Search error:', error);
            this.showError('Network error occurred. Please try again.');
        } finally {
            this.setLoadingState(false);
        }
    }

    displayResults(data) {
        const resultsContainer = document.getElementById('resultsContainer');
        
        // Update case information
        document.getElementById('parties').textContent = data.parties || 'Not available';
        document.getElementById('filingDate').textContent = data.filing_date || 'Not available';
        document.getElementById('hearingDate').textContent = data.hearing_date || 'Not available';
        
        // Handle PDF links
        const pdfContainer = document.getElementById('pdfLinksContainer');
        const pdfLinksDiv = document.getElementById('pdfLinks');
        
        if (data.pdf_links && data.pdf_links.length > 0) {
            pdfLinksDiv.innerHTML = '';
            
            data.pdf_links.forEach((link, index) => {
                const linkElement = document.createElement('a');
                linkElement.href = '#';
                linkElement.className = 'btn btn-download';
                linkElement.textContent = link.text || `Document ${index + 1}`;
                linkElement.onclick = (e) => {
                    e.preventDefault();
                    this.downloadPDF(link.url);
                };
                
                pdfLinksDiv.appendChild(linkElement);
            });
            
            pdfContainer.style.display = 'block';
        } else {
            pdfContainer.style.display = 'none';
        }
        
        // Show results with animation
        resultsContainer.style.display = 'block';
        resultsContainer.classList.add('fade-in');
    }

    async downloadPDF(pdfUrl) {
        try {
            const encodedUrl = encodeURIComponent(pdfUrl);
            const response = await fetch(`${this.apiBase}/download/${encodedUrl}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `case_document_${Date.now()}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                this.showError('Failed to download PDF');
            }
        } catch (error) {
            console.error('PDF download error:', error);
            this.showError('Error downloading PDF');
        }
    }

    setLoadingState(loading) {
        const searchBtn = document.getElementById('searchBtn');
        const searchBtnText = document.getElementById('searchBtnText');
        const searchBtnLoader = document.getElementById('searchBtnLoader');
        
        if (loading) {
            searchBtn.disabled = true;
            searchBtnText.style.display = 'none';
            searchBtnLoader.style.display = 'inline-block';
        } else {
            searchBtn.disabled = false;
            searchBtnText.style.display = 'inline-block';
            searchBtnLoader.style.display = 'none';
        }
    }

    showError(message) {
        const errorContainer = document.getElementById('errorContainer');
        const errorMessage = document.getElementById('errorMessage');
        
        errorMessage.textContent = message;
        errorContainer.style.display = 'block';
        
        // Auto-hide after 10 seconds
        setTimeout(() => {
            this.hideError();
        }, 10000);
    }

    hideError() {
        const errorContainer = document.getElementById('errorContainer');
        errorContainer.style.display = 'none';
    }

    hideResults() {
        const resultsContainer = document.getElementById('resultsContainer');
        resultsContainer.style.display = 'none';
        resultsContainer.classList.remove('fade-in');
    }

    showCaptchaField() {
        const captchaGroup = document.getElementById('captchaGroup');
        captchaGroup.style.display = 'block';
    }

    // Utility methods
    formatDate(dateString) {
        if (!dateString) return 'Not available';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-IN', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        } catch (error) {
            return dateString;
        }
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CourtDataFetcher();
});

// Global error handler
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

// Service worker registration (if needed for offline functionality)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Register service worker if available
        // navigator.serviceWorker.register('/sw.js');
    });
}