# 🔒 PII Redaction Tool

A powerful web application for detecting and redacting Personally Identifiable Information (PII) from documents. Built with Flask, spaCy, and modern web technologies.

## 📋 Features

- **Multiple Input Methods**: Upload PDF files or paste text directly
- **Smart PII Detection**: Uses spaCy NER and regex patterns to detect:
  - 📧 Email addresses
  - 📱 Phone numbers
  - 👤 Person names
  - 🏠 Physical addresses (streets, cities, zip codes)
- **Customizable Redaction**: Toggle which PII types to redact
- **Export Options**: Download redacted content as TXT or PDF
- **Dark Mode**: Toggle between light and dark themes
- **Detailed Logging**: View all detected and redacted PII items
- **Modern UI**: Beautiful gradient design with smooth animations

## 🏗️ Project Structure

```
PYTHON_STACK/
├── public/
│   ├── app.js          # Frontend JavaScript logic
│   ├── index.html      # Main HTML structure
│   └── style.css       # Styling and themes
├── app.py              # Flask backend server
├── Dockerfile          # Docker containerization
└── requirements.txt    # Python dependencies
```

## 📦 Installation

### Prerequisites

- Python 3.11+
- pip
- Docker (optional, for containerized deployment)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/subhammahankud/pii-redaction-tool.git
   cd PYTHON_STACK
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download spaCy language model**
   ```bash
   python -m spacy download en_core_web_sm
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   - Open your browser and navigate to `http://localhost:5000`

## 🐳 Docker Deployment

### Build and Run

1. **Build the Docker image**
   ```bash
   docker build -t pii-redaction-tool .
   ```

2. **Run the container**
   ```bash
   docker run -d -p 5000:5000 --name pii-app pii-redaction-tool
   ```

3. **Access the application**
   - Navigate to `http://localhost:5000`

### Docker Commands

```bash
# View logs
docker logs pii-app

# Stop container
docker stop pii-app

# Remove container
docker rm pii-app

# Remove image
docker rmi pii-redaction-tool
```

## 🚀 Usage

1. **Upload a PDF** or **Paste Text**
   - Click the upload area to select a PDF file
   - Or drag and drop a PDF file
   - Or paste text directly into the text area

2. **Configure Redaction Settings**
   - Toggle checkboxes to select which PII types to redact:
     - ✅ Emails
     - ✅ Phone Numbers
     - ✅ Names
     - ✅ Addresses

3. **Click "Redact PII"**
   - View original and redacted text side-by-side
   - Check the redaction log for details

4. **Download Results**
   - Download as TXT file
   - Download as PDF file

5. **Reset**
   - Click the reset button (🔄) to clear all fields

## 🛠️ Technology Stack

### Backend
- **Flask 3.0.0**: Web framework
- **spaCy 3.7.2**: Natural Language Processing for Named Entity Recognition
- **PyPDF2 3.0.1**: PDF text extraction
- **ReportLab 4.0.7**: PDF generation
- **Gunicorn**: Production WSGI server

### Frontend
- **HTML5**: Structure
- **CSS3**: Styling with CSS variables for theming
- **Vanilla JavaScript**: Client-side logic
- **Responsive Design**: Mobile-friendly interface

## 🔍 PII Detection Methods

### Email Addresses
- Regex pattern matching for standard email formats
- Supports various TLDs and email structures

### Phone Numbers
- Multiple format support (US and international)
- Handles spaces, dashes, parentheses
- Examples: `(123) 456-7890`, `+1-234-567-8900`

### Names
- **spaCy NER**: ML-based named entity recognition
- **Context-aware filtering**: Excludes form labels and headers
- **Label-based detection**: Identifies names following field labels

### Addresses
- Street addresses with common suffixes (St, Ave, Rd, etc.)
- City names with contextual validation
- State abbreviations
- ZIP codes (5 or 9 digit formats)
- Building components (Tower, Suite, Floor, etc.)

## ⚙️ Configuration

### Port Configuration
Default port is `5000`. To change:

**Local:**
```python
# In app.py
app.run(port=5000, debug=True)
```

**Docker:**
```bash
docker run -p 5000:5000 pii-redaction-tool
```

### Worker Configuration
Gunicorn uses 4 workers by default. To change:

```dockerfile
# In Dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "8", "--timeout", "120", "app:app"]
```

## 🎨 Themes

The application supports light and dark modes:
- Click the 🌙/☀️ button in the header to toggle themes
- Theme preference is maintained during session

### Container Not Accessible
- Use `http://localhost:5000`
- Check if container is running: `docker ps`
- View logs: `docker logs pii-app`

## 📝 API Endpoints

### `POST /extract-pdf`
Extract text from PDF file
- **Input**: `multipart/form-data` with PDF file
- **Output**: Plain text

### `POST /redact`
Perform PII redaction
- **Input**: JSON `{ text, settings }`
- **Output**: JSON `{ redacted, log }`

### `POST /download-txt`
Download redacted text as TXT
- **Input**: JSON `{ redacted }`
- **Output**: File download

### `POST /download-pdf`
Download redacted text as PDF
- **Input**: JSON `{ redacted }`
- **Output**: File download

## 🔐 Security Considerations

- All processing is done server-side
- No data is stored permanently
- Files are processed in memory
- No external API calls for PII detection
- Suitable for sensitive document handling

**Built with using Flask and spaCy**