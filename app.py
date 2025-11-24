import re
import io
from flask import Flask, request, jsonify, send_file, send_from_directory
from PyPDF2 import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import spacy

app = Flask(__name__, static_folder='public', static_url_path='')

# Load spaCy model for NER
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("spaCy model not found. Install with: python -m spacy download en_core_web_sm")
    nlp = None

# Common form field labels and building-related words to exclude from name detection
FIELD_LABELS = {
    'name', 'email', 'phone', 'address', 'contact', 'emergency', 'customer',
    'employee', 'client', 'record', 'information', 'details', 'subject',
    'floor', 'tower', 'building', 'suite', 'unit', 'room', 'apt', 'apartment',
    'office', 'level', 'wing', 'library', 'card', 'checkout', 'borrower',
    'book', 'title', 'author', 'publisher', 'notes', 'date', 'return', 'manager',
    'to', 'from', 'cc', 'bcc', 'subject'
}

# Email regex
EMAIL_REGEX = re.compile(r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[A-Za-z]{2,}\b', re.IGNORECASE)

# Phone regex - Updated to handle spaces around delimiters (common in PDF extraction)
PHONE_REGEX = re.compile(
    r'(?:'
    r'\+?\d{1,3}\s*[-.\s]\s*\d{10,14}|'
    r'\+?\d{10,15}|'
    r'(?:\+?1\s*[-.\s]?\s*)?'
    r'(?:\(\s*\d{3}\s*\)|\d{3})'
    r'\s*[-.\s]\s*\d{3}\s*[-.\s]\s*\d{4}'
    r')\b',
    re.VERBOSE
)

# Zipcode regex (US format)
ZIPCODE_REGEX = re.compile(r'\b\d{5}(?:-\d{4})?\b')

# Street address regex
ADDRESS_REGEX = re.compile(
    r'(?:\b\d{1,5}\s+[A-Za-z0-9\s\.\-]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Boulevard|Blvd|Drive|Dr|Way|Court|Ct|Circle|Cir|Place|Pl|Parkway|Pkwy)\b'
    r'|\d{1,3}(?:st|nd|rd|th)\s+Floor|Floor\s+\d{1,3}|Tower\s+[A-Z]|Building\s+[A-Z0-9]+)',
    re.IGNORECASE
)

# City name pattern
CITY_REGEX = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?=\s*(?:,\s*\d{5}|,\s*[A-Z]{2}\b|\.\s*$))')

# State abbreviation pattern
STATE_ABBREV_REGEX = re.compile(r'\b[A-Z]{2}\b(?=\s*(?:,|\.|$|\n))')

# Building components
BUILDING_COMPONENT_REGEX = re.compile(r'(?:Tower|Building|Suite|Unit|Room|Apt|Apartment)\s+[A-Z0-9]+', re.IGNORECASE)

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

def normalize_whitespace(text):
    """Normalize whitespace in PDF-extracted text while preserving structure.
    
    Returns: (normalized_text, position_map)
    - normalized_text: text with normalized whitespace
    - position_map: list mapping each character position in normalized text to original position
    """
    normalized = []
    position_map = []
    i = 0
    
    while i < len(text):
        char = text[i]
        
        # Handle newlines and paragraph breaks
        if char == '\n':
            normalized.append('\n')
            position_map.append(i)
            i += 1
        # Handle spaces and tabs
        elif char in ' \t':
            # Collect all consecutive whitespace
            space_start = i
            while i < len(text) and text[i] in ' \t':
                i += 1
            # Replace with single space (unless at line start/end)
            if normalized and normalized[-1] != '\n' and i < len(text) and text[i] != '\n':
                normalized.append(' ')
                position_map.append(space_start)
        else:
            normalized.append(char)
            position_map.append(i)
            i += 1
    
    return ''.join(normalized), position_map

def map_positions_back(matches, position_map):
    """Map positions from normalized text back to original text positions."""
    mapped_matches = []
    for start, end, text, typ in matches:
        if start < len(position_map) and end <= len(position_map):
            orig_start = position_map[start]
            orig_end = position_map[end - 1] + 1 if end > 0 else position_map[0]
            mapped_matches.append((orig_start, orig_end, text, typ))
    return mapped_matches

@app.route('/extract-pdf', methods=['POST'])
def extract_pdf():
    """Extract text from uploaded PDF using PyPDF2."""
    if 'file' not in request.files:
        return "No file part", 400
    f = request.files['file']
    if f.filename == '':
        return "No file selected", 400

    try:
        reader = PdfReader(f.stream)
        text_parts = []
        for page in reader.pages:
            try:
                text_parts.append(page.extract_text() or '')
            except Exception:
                text_parts.append('')
        all_text = "\n".join(text_parts)
        return all_text
    except Exception as e:
        return f"Failed to parse PDF: {str(e)}", 500

def is_field_label(text):
    """Check if text is a common form field label."""
    cleaned = text.lower().strip(':').strip()
    if cleaned in FIELD_LABELS:
        return True
    words = cleaned.split()
    for word in words:
        if word in FIELD_LABELS:
            return True
    return False

def extract_names_ner(text):
    """Extract person names using spaCy NER with filtering and label-based detection."""
    matches = []
    
    # First, look for names after common field labels (more reliable for forms)
    # Updated pattern to NOT capture colon-separated values on the same line
    label_pattern = re.compile(
        r'(?:Name|Manager|Supervisor|Contact|Employee|Customer|Client|Borrower|Author|Reviewer|From)\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+?)(?=\s*\n|$)',
        re.IGNORECASE
    )
    
    for m in label_pattern.finditer(text):
        name_text = m.group(1).strip()
        # Remove any trailing colons or punctuation that might have been captured
        name_text = re.sub(r'[:\s]+$', '', name_text)
        
        name_start = m.start(1)
        name_end = name_start + len(name_text)
        
        # Make sure it's not a field label itself
        if not is_field_label(name_text):
            matches.append((name_start, name_end, name_text))
    
    # Then use spaCy or regex for other names
    if nlp is None:
        # Enhanced regex fallback with better name detection
        name_regex = re.compile(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b')
        for m in name_regex.finditer(text):
            name_text = m.group(0)
            
            # Skip if already matched by label pattern
            already_matched = False
            for start, end, _ in matches:
                if not (m.end() <= start or m.start() >= end):
                    already_matched = True
                    break
            if already_matched:
                continue
            
            if is_field_label(name_text):
                continue
            
            # Check context
            preceding_text = text[max(0, m.start()-20):m.start()]
            following_text = text[m.start():m.end()+10]
            
            # Skip if at the very start of the document (likely a title)
            if m.start() < 5:
                continue
            
            # Skip if preceded by newline or start of text (likely a header/title)
            if m.start() == 0 or (m.start() >= 1 and text[m.start()-1] == '\n'):
                # Check if there's a colon or field label pattern after it
                if not re.search(r':', following_text[:20]):
                    continue
            
            # Skip city names (appear before zip codes or periods)
            if re.search(r'^[A-Z][a-z]+(?:,\s*\d{5}|\.\s*)', following_text):
                continue
            # Skip building/floor references
            ordinal_pattern = r'\d+(?:st|nd|rd|th)\s+'
            if re.search(ordinal_pattern, preceding_text):
                continue
            
            matches.append((m.start(), m.end(), name_text))
    else:
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                # Skip if already matched by label pattern
                already_matched = False
                for start, end, _ in matches:
                    if not (ent.end_char <= start or ent.start_char >= end):
                        already_matched = True
                        break
                if already_matched:
                    continue
                
                following_text = text[ent.end_char:ent.end_char+10]
                preceding_text = text[max(0, ent.start_char-20):ent.start_char]
                
                word_count = len(ent.text.split())
                
                # Skip if at the very start of the document (likely a title)
                if ent.start_char < 5:
                    continue
                
                # Skip if preceded by newline or start of text (likely a header/title)
                if ent.start_char == 0 or (ent.start_char >= 1 and text[ent.start_char-1] == '\n'):
                    # Check if there's a colon or field label pattern after it
                    if not re.search(r':', following_text[:20]):
                        continue
                
                # More lenient for single-word names if they follow a title
                if word_count == 1:
                    title_pattern = r'(?:Dr|Mr|Ms|Mrs|Prof)\.?\s*'
                    has_title = re.search(title_pattern, preceding_text, re.IGNORECASE)
                    if not has_title:
                        continue
                
                # Skip city names (appear before zip codes or periods)
                if re.match(r'(?:,\s*\d{5}|\.\s*)', following_text):
                    continue
                # Skip building references
                ordinal_pattern = r'\d+(?:st|nd|rd|th)\s+'
                if re.search(ordinal_pattern, preceding_text):
                    continue
                
                matches.append((ent.start_char, ent.end_char, ent.text))
    
    return matches

def extract_emails(text):
    """Extract email addresses using regex."""
    matches = []
    for m in EMAIL_REGEX.finditer(text):
        matches.append((m.start(), m.end(), m.group(0)))
    return matches

def extract_phones(text):
    """Extract phone numbers using regex."""
    matches = []
    for m in PHONE_REGEX.finditer(text):
        matches.append((m.start(), m.end(), m.group(0)))
    return matches

def extract_zipcodes(text):
    """Extract ZIP codes."""
    matches = []
    for m in ZIPCODE_REGEX.finditer(text):
        matches.append((m.start(), m.end(), m.group(0)))
    return matches

def extract_addresses(text):
    """Extract street addresses, building components, and city names."""
    addresses = []
    
    # Extract standard street addresses
    for m in ADDRESS_REGEX.finditer(text):
        addresses.append((m.start(), m.end(), m.group(0)))
    
    # Extract building components (Tower B, Suite 100, etc.)
    for m in BUILDING_COMPONENT_REGEX.finditer(text):
        overlaps = False
        for start, end, _ in addresses:
            if not (m.end() <= start or m.start() >= end):
                overlaps = True
                break
        if not overlaps:
            addresses.append((m.start(), m.end(), m.group(0)))
    
    # Extract cities from address patterns
    address_city_pattern = re.compile(
        r'(?:\d{1,5}\s+[A-Za-z]+\s+(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd|Way|Court|Ct|Place|Pl),\s+)'
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        re.IGNORECASE
    )
    
    for m in address_city_pattern.finditer(text):
        city_start = m.start(1)
        city_end = m.end(1)
        city_text = m.group(1)
        
        overlaps = False
        for start, end, _ in addresses:
            if not (city_end <= start or city_start >= end):
                overlaps = True
                break
        if not overlaps:
            addresses.append((city_start, city_end, city_text))
    
    # Extract standalone city names
    for m in CITY_REGEX.finditer(text):
        overlaps = False
        for start, end, _ in addresses:
            if not (m.end() <= start or m.start() >= end):
                overlaps = True
                break
        if not overlaps:
            addresses.append((m.start(), m.end(), m.group(0)))
    
    # Extract state abbreviations when they follow city names
    for m in STATE_ABBREV_REGEX.finditer(text):
        preceding_text = text[max(0, m.start()-30):m.start()]
        city_pattern = r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*'
        location_pattern = r'Location:.*?'
        
        has_city_before = re.search(city_pattern, preceding_text)
        has_location_field = re.search(location_pattern, preceding_text, re.IGNORECASE)
        
        if has_city_before or has_location_field:
            overlaps = False
            for start, end, _ in addresses:
                if not (m.end() <= start or m.start() >= end):
                    overlaps = True
                    break
            if not overlaps:
                addresses.append((m.start(), m.end(), m.group(0)))
    
    return addresses

def perform_redaction(text, settings):
    """Perform NER-based redaction on text."""
    # Normalize whitespace for better NER detection
    normalized_text, position_map = normalize_whitespace(text)
    
    log = []
    counters = {'emails': 1, 'phones': 1, 'names': 1, 'addresses': 1, 'zipcodes': 1}
    
    all_matches = []
    
    # Extract entities from normalized text
    if settings.get('emails', False):
        for start, end, original in extract_emails(normalized_text):
            all_matches.append((start, end, original, 'emails'))
    
    if settings.get('phones', False):
        for start, end, original in extract_phones(normalized_text):
            all_matches.append((start, end, original, 'phones'))
    
    if settings.get('addresses', False):
        for start, end, original in extract_addresses(normalized_text):
            all_matches.append((start, end, original, 'addresses'))
        
        for start, end, original in extract_zipcodes(normalized_text):
            all_matches.append((start, end, original, 'zipcodes'))
    
    if settings.get('names', False):
        for start, end, original in extract_names_ner(normalized_text):
            all_matches.append((start, end, original, 'names'))
    
    # Remove overlaps
    all_matches = remove_overlaps(all_matches)
    
    # Map positions back to original text
    all_matches = map_positions_back(all_matches, position_map)
    
    # Sort by position
    all_matches.sort()
    
    # Perform redaction on original text
    redacted = text
    offset = 0
    
    for start, end, original, typ in all_matches:
        adj_start = start + offset
        adj_end = end + offset
        
        if typ == 'names':
            token = f"[NAME_{counters['names']}]"
        elif typ == 'emails':
            token = f"[EMAIL_{counters['emails']}]"
        elif typ == 'phones':
            token = f"[PHONE_{counters['phones']}]"
        elif typ == 'addresses':
            token = f"[ADDRESS_{counters['addresses']}]"
        elif typ == 'zipcodes':
            token = f"[ZIPCODE_{counters['zipcodes']}]"
        else:
            token = f"[{typ.upper()}_{counters[typ]}]"
        
        counters[typ] += 1
        log.append(f'{typ.upper()}: "{original}" -> {token}')
        
        redacted = redacted[:adj_start] + token + redacted[adj_end:]
        offset += len(token) - (end - start)
    
    return redacted, log

def remove_overlaps(matches):
    """Remove overlapping matches, prioritizing more specific entity types."""
    if not matches:
        return []
    
    type_priority = {'emails': 0, 'phones': 1, 'zipcodes': 2, 'addresses': 3, 'names': 4}
    
    sorted_matches = sorted(matches, key=lambda x: (x[0], type_priority.get(x[3], 99), -(x[1] - x[0])))
    
    result = []
    for match in sorted_matches:
        start, end, original, typ = match
        overlaps = False
        for r_start, r_end, _, _ in result:
            if not (end <= r_start or start >= r_end):
                overlaps = True
                break
        if not overlaps:
            result.append(match)
    
    return result

@app.route('/redact', methods=['POST'])
def redact():
    """Redact text based on settings."""
    j = request.get_json(force=True)
    text = j.get('text', '')
    settings = j.get('settings', {})

    redacted_text, log = perform_redaction(text, settings)
    return jsonify({'redacted': redacted_text, 'log': log})

@app.route('/download-txt', methods=['POST'])
def download_txt():
    """Download redacted text as TXT file."""
    j = request.get_json(force=True)
    redacted = j.get('redacted', '')
    b = io.BytesIO()
    b.write(redacted.encode('utf-8'))
    b.seek(0)
    return send_file(b, download_name='redacted.txt', as_attachment=True, mimetype='text/plain')

@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    """Download redacted text as PDF file."""
    j = request.get_json(force=True)
    redacted = j.get('redacted', '')

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    left_margin = 40
    top = height - 40
    line_height = 12
    x = left_margin
    y = top

    for paragraph in redacted.split('\n'):
        words = paragraph.split(' ')
        line = ''
        for w in words:
            if len(line + ' ' + w) > 90:
                c.drawString(x, y, line.strip())
                y -= line_height
                line = w + ' '
                if y < 40:
                    c.showPage()
                    y = top
            else:
                line += w + ' '
        c.drawString(x, y, line.strip())
        y -= line_height
        if y < 40:
            c.showPage()
            y = top

    c.save()
    buffer.seek(0)
    return send_file(buffer, download_name='redacted.pdf', as_attachment=True, mimetype='application/pdf')

if __name__ == '__main__':
    app.run(port=5000, debug=True)