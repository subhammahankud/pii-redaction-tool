const pdfInput = document.getElementById('pdfInput');
    const textInput = document.getElementById('textInput');
    const redactBtn = document.getElementById('redactBtn');
    const originalOutput = document.getElementById('originalOutput');
    const redactedOutput = document.getElementById('redactedOutput');
    const logOutput = document.getElementById('logOutput');
    const downloadTxtBtn = document.getElementById('downloadTxtBtn');
    const downloadPdfBtn = document.getElementById('downloadPdfBtn');
    const uploadArea = document.getElementById('uploadArea');
    const fileName = document.getElementById('fileName');
    const loading = document.getElementById('loading');
    const themeToggle = document.getElementById('themeToggle');
    const resetBtn = document.getElementById('resetBtn');

    // Theme toggle functionality
    let isDark = false;
    themeToggle.addEventListener('click', () => {
      isDark = !isDark;
      document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
      themeToggle.textContent = isDark ? '☀️' : '🌙';
      themeToggle.title = isDark ? 'Toggle Light Mode' : 'Toggle Dark Mode';
    });

    // Reset functionality
    resetBtn.addEventListener('click', () => {
      if (confirm('Are you sure you want to reset all fields?')) {
        // Clear file input
        pdfInput.value = '';
        fileName.textContent = '';
        
        // Clear text input
        textInput.value = '';
        
        // Clear outputs
        originalOutput.value = '';
        redactedOutput.value = '';
        logOutput.value = '';
        
        // Reset checkboxes to default (all checked)
        document.getElementById('redactEmails').checked = true;
        document.getElementById('redactPhones').checked = true;
        document.getElementById('redactNames').checked = true;
        document.getElementById('redactAddresses').checked = true;
        
        // Disable download buttons
        downloadTxtBtn.disabled = true;
        downloadPdfBtn.disabled = true;
        
        // Show confirmation
        loading.style.display = 'block';
        loading.innerHTML = '<div style="color: #48bb78; font-weight: 600;">✓ Reset Complete!</div>';
        setTimeout(() => {
          loading.style.display = 'none';
          loading.innerHTML = '<div class="spinner"></div><div>Processing...</div>';
        }, 1500);
      }
    });

    // Upload area interactions
    uploadArea.addEventListener('click', () => pdfInput.click());

    uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
      uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadArea.classList.remove('dragover');
      if (e.dataTransfer.files.length) {
        pdfInput.files = e.dataTransfer.files;
        fileName.textContent = `📎 ${e.dataTransfer.files[0].name}`;
      }
    });

    pdfInput.addEventListener('change', () => {
      if (pdfInput.files.length) {
        fileName.textContent = `📎 ${pdfInput.files[0].name}`;
      }
    });

    redactBtn.addEventListener('click', async () => {
      loading.style.display = 'block';
      let text = textInput.value || '';
      
      try {
        if (pdfInput.files && pdfInput.files[0]) {
          const fd = new FormData();
          fd.append('file', pdfInput.files[0]);
          const res = await fetch('/extract-pdf', { method: 'POST', body: fd });
          if (!res.ok) {
            const t = await res.text();
            alert('PDF extraction failed: ' + t);
            loading.style.display = 'none';
            return;
          }
          text = await res.text();
        }

        originalOutput.value = text;

        const settings = {
          emails: document.getElementById('redactEmails').checked,
          phones: document.getElementById('redactPhones').checked,
          names: document.getElementById('redactNames').checked,
          addresses: document.getElementById('redactAddresses').checked
        };

        const r = await fetch('/redact', {
          method: 'POST', 
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, settings })
        });

        const data = await r.json();
        redactedOutput.value = data.redacted;
        logOutput.value = data.log.join('\n');

        if (data.redacted && data.redacted.length > 0) {
          downloadTxtBtn.disabled = false;
          downloadPdfBtn.disabled = false;
        }
      } catch (error) {
        alert('Error: ' + error.message);
      } finally {
        loading.style.display = 'none';
      }
    });

    downloadTxtBtn.addEventListener('click', async () => {
      const redacted = redactedOutput.value || '';
      const res = await fetch('/download-txt', {
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ redacted })
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'redacted.txt';
      a.click();
      URL.revokeObjectURL(url);
    });

    downloadPdfBtn.addEventListener('click', async () => {
      const redacted = redactedOutput.value || '';
      const res = await fetch('/download-pdf', {
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ redacted })
      });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'redacted.pdf';
      a.click();
      URL.revokeObjectURL(url);
    });