document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const messagesViewport = document.getElementById('messagesViewport');
  const welcomeCard = document.getElementById('welcomeCard');
  const queryInput = document.getElementById('queryInput');
  const sendBtn = document.getElementById('sendBtn');
  const sendBtnIcon = document.getElementById('sendBtnIcon');
  const attachBtn = document.getElementById('attachBtn');
  const fileInput = document.getElementById('fileInput');
  const fileDropArea = document.getElementById('fileDropArea');
  const attachedFilesList = document.getElementById('attachedFilesList');
  const inputPills = document.getElementById('inputPills');
  const exportBtn = document.getElementById('exportBtn');
  const clearBtn = document.getElementById('clearBtn');
  const modelSelector = document.getElementById('modelSelector');
  const personaButtons = document.querySelectorAll('.persona-btn');
  const activePersonaIcon = document.getElementById('activePersonaIcon');
  const activePersonaName = document.getElementById('activePersonaName');
  const headerMetric = document.getElementById('headerMetric');
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');
  const suggestionChips = document.querySelectorAll('.chip');

  // Application State
  let activePersona = 'researcher';
  let activeModel = 'gemini-3.6-flash';
  let isStreaming = false;
  let abortController = null;
  let attachedFiles = []; // [{name: 'filename', content: '...', lines: 10}]

  // Configure Marked for code blocks
  if (window.marked) {
    marked.setOptions({
      highlight: function(code, lang) {
        if (window.hljs) {
          const language = hljs.getLanguage(lang) ? lang : 'plaintext';
          return hljs.highlight(code, { language }).value;
        }
        return code;
      },
      breaks: true,
      gfm: true
    });
  }

  // Auto-resize textarea
  queryInput.addEventListener('input', () => {
    queryInput.style.height = 'auto';
    queryInput.style.height = Math.min(queryInput.scrollHeight, 180) + 'px';
  });

  // Toggle Sidebar on mobile
  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
  }

  // Suggestion chips click
  suggestionChips.forEach(chip => {
    chip.addEventListener('click', () => {
      queryInput.value = chip.getAttribute('data-query');
      queryInput.focus();
      handleSend();
    });
  });

  // Persona switching
  personaButtons.forEach(btn => {
    btn.addEventListener('click', async () => {
      const targetPersona = btn.getAttribute('data-persona');
      if (targetPersona === activePersona) return;
      await switchPersona(targetPersona);
    });
  });

  async function switchPersona(personaKey) {
    try {
      const res = await fetch('/api/persona', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ persona: personaKey })
      });
      const data = await res.json();
      if (data.success) {
        activePersona = personaKey;
        personaButtons.forEach(b => {
          b.classList.toggle('active', b.getAttribute('data-persona') === personaKey);
        });
        activePersonaIcon.textContent = data.icon;
        activePersonaName.textContent = data.name;

        appendSystemAnnouncement(`🔄 Switched to: ${data.icon} ${data.name}\n"${data.system_instruction}"`);
      }
    } catch (err) {
      console.error('Failed to switch persona:', err);
    }
  }

  // Model selection
  modelSelector.addEventListener('change', async () => {
    const chosenModel = modelSelector.value;
    try {
      const res = await fetch('/api/model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: chosenModel })
      });
      const data = await res.json();
      if (data.success) {
        activeModel = chosenModel;
        appendSystemAnnouncement(`🤖 Switched active Gemini model to: ${chosenModel}`);
      }
    } catch (err) {
      console.error('Failed to switch model:', err);
    }
  });

  // File Upload Handlers (Click + Drag & Drop)
  attachBtn.addEventListener('click', () => fileInput.click());
  fileDropArea.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
    fileInput.value = '';
  });

  ['dragenter', 'dragover'].forEach(name => {
    fileDropArea.addEventListener(name, (e) => {
      e.preventDefault();
      fileDropArea.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(name => {
    fileDropArea.addEventListener(name, (e) => {
      e.preventDefault();
      fileDropArea.classList.remove('dragover');
    });
  });

  fileDropArea.addEventListener('drop', (e) => {
    if (e.dataTransfer.files.length) {
      handleFiles(e.dataTransfer.files);
    }
  });

  // Also support drag-and-drop into chat viewport
  messagesViewport.addEventListener('dragover', (e) => e.preventDefault());
  messagesViewport.addEventListener('drop', (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length) {
      handleFiles(e.dataTransfer.files);
    }
  });

  async function handleFiles(files) {
    for (const file of files) {
      if (file.size > 300 * 1024) {
        alert(`File ${file.name} is too large (>300 KB limit).`);
        continue;
      }
      try {
        const text = await file.text();
        const lines = text.split('\n').length;
        attachedFiles.push({
          name: file.name,
          content: text,
          lines: lines
        });
      } catch (err) {
        console.error('Error reading file:', err);
      }
    }
    renderAttachedFiles();
  }

  function renderAttachedFiles() {
    attachedFilesList.innerHTML = '';
    inputPills.innerHTML = '';

    attachedFiles.forEach((file, index) => {
      // Sidebar pill
      const pill = document.createElement('div');
      pill.className = 'attached-pill';
      pill.innerHTML = `
        <span class="attached-pill-name" title="${file.name}">📄 ${file.name} (${file.lines}L)</span>
        <button class="attached-pill-del" data-index="${index}">✕</button>
      `;
      attachedFilesList.appendChild(pill);

      // Input preview pill
      const inputPill = document.createElement('div');
      inputPill.className = 'attached-pill';
      inputPill.innerHTML = `
        <span class="attached-pill-name">📎 ${file.name}</span>
        <button class="attached-pill-del" data-index="${index}">✕</button>
      `;
      inputPills.appendChild(inputPill);
    });

    document.querySelectorAll('.attached-pill-del').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const idx = parseInt(e.target.getAttribute('data-index'));
        attachedFiles.splice(idx, 1);
        renderAttachedFiles();
      });
    });
  }

  // Clear Chat
  clearBtn.addEventListener('click', async () => {
    if (confirm('Clear all conversation memory and reset chat?')) {
      await fetch('/api/clear', { method: 'POST' });
      messagesViewport.innerHTML = '';
      if (welcomeCard) messagesViewport.appendChild(welcomeCard);
      attachedFiles = [];
      renderAttachedFiles();
      appendSystemAnnouncement('🧹 Conversation memory reset.');
    }
  });

  // Export Session
  exportBtn.addEventListener('click', () => {
    window.open('/api/export', '_blank');
  });

  // Handle Input Keypress (Enter vs Shift+Enter)
  queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  sendBtn.addEventListener('click', handleSend);

  async function handleSend() {
    if (isStreaming) {
      // Abort ongoing generation
      if (abortController) {
        abortController.abort();
      }
      return;
    }

    const rawText = queryInput.value.trim();
    if (!rawText && attachedFiles.length === 0) return;

    // Remove welcome card on first message
    if (welcomeCard && welcomeCard.parentNode) {
      welcomeCard.remove();
    }

    // Check for client-side slash commands
    const cmd = rawText.toLowerCase();
    if (cmd === '/coder') {
      await switchPersona('coder');
      queryInput.value = '';
      return;
    } else if (cmd === '/writer') {
      await switchPersona('writer');
      queryInput.value = '';
      return;
    } else if (cmd === '/researcher' || cmd === '/default') {
      await switchPersona('researcher');
      queryInput.value = '';
      return;
    } else if (cmd === '/clear') {
      clearBtn.click();
      queryInput.value = '';
      return;
    } else if (cmd.startsWith('/save')) {
      exportBtn.click();
      queryInput.value = '';
      return;
    }

    // Reset textarea
    queryInput.value = '';
    queryInput.style.height = 'auto';

    // Build query payload with attached files
    const filesPayload = [...attachedFiles];
    attachedFiles = [];
    renderAttachedFiles();

    // Render User Message
    appendUserMessage(rawText, filesPayload);

    // Prepare Bot Message Container
    const { card, contentEl, metricsEl } = appendBotMessagePlaceholder();

    // Start Streaming
    isStreaming = true;
    sendBtn.classList.add('stop-btn');
    sendBtnIcon.textContent = '⏹';
    headerMetric.textContent = '⏱️ Streaming...';

    abortController = new AbortController();
    let accumulatedMarkdown = '';

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: rawText,
          files: filesPayload
        }),
        signal: abortController.signal
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(errText || `Server error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // keep last incomplete line

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (dataStr === '[DONE]') continue;
            try {
              const msg = JSON.parse(dataStr);
              if (msg.event === 'token') {
                accumulatedMarkdown += msg.text;
                contentEl.innerHTML = marked.parse(accumulatedMarkdown) + '<span class="cursor-pulse"></span>';
                scrollToBottom();
              } else if (msg.event === 'done') {
                contentEl.innerHTML = marked.parse(accumulatedMarkdown);
                metricsEl.textContent = msg.metrics || '';
                headerMetric.textContent = msg.metrics || '⏱️ Complete';
              } else if (msg.event === 'error') {
                contentEl.innerHTML = `<span style="color: var(--accent-red)">⚠️ ${msg.message}</span>`;
                headerMetric.textContent = '⚠️ Error';
              }
            } catch (jsonErr) {
              console.warn('Could not parse SSE JSON:', jsonErr);
            }
          }
        }
      }

      // Final pass on code highlighting
      if (window.hljs) {
        contentEl.querySelectorAll('pre code').forEach(block => {
          hljs.highlightElement(block);
        });
      }

    } catch (err) {
      if (err.name === 'AbortError') {
        contentEl.innerHTML = marked.parse(accumulatedMarkdown) + '\n\n*(Generation stopped by user)*';
        metricsEl.textContent = 'Interrupted';
        headerMetric.textContent = '⏹️ Interrupted';
      } else {
        contentEl.innerHTML = `<span style="color: var(--accent-red)">⚠️ Error: ${err.message}</span>`;
        headerMetric.textContent = '⚠️ Failed';
      }
    } finally {
      isStreaming = false;
      abortController = null;
      sendBtn.classList.remove('stop-btn');
      sendBtnIcon.textContent = '➤';
      scrollToBottom();
    }
  }

  // Helper: Append User Message
  function appendUserMessage(text, files) {
    const row = document.createElement('div');
    row.className = 'message-row user';

    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    let filesHtml = '';
    if (files && files.length) {
      filesHtml = `<div class="message-files-tag" style="font-size: 11px; margin-bottom: 6px; color: var(--accent-blue)">` +
        files.map(f => `📄 ${f.name} (${f.lines} lines)`).join(', ') + `</div>`;
    }

    row.innerHTML = `
      <div class="message-sender-meta"><span>You</span> • <span>${now}</span></div>
      <div class="message-card user-card">
        ${filesHtml}
        <div>${escapeHtml(text)}</div>
      </div>
    `;
    messagesViewport.appendChild(row);
    scrollToBottom();
  }

  // Helper: Append Bot Message Placeholder
  function appendBotMessagePlaceholder() {
    const row = document.createElement('div');
    row.className = 'message-row bot';

    const activeBtn = document.querySelector(`.persona-btn[data-persona="${activePersona}"]`);
    const icon = activeBtn ? activeBtn.querySelector('.p-icon').textContent : '🔬';
    const name = activeBtn ? activeBtn.querySelector('.p-name').textContent : 'Research Assistant';
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    row.innerHTML = `
      <div class="message-sender-meta"><span>${icon} ${name}</span> • <span>${now}</span></div>
      <div class="message-card bot-card">
        <div class="bot-content"><span class="cursor-pulse"></span></div>
        <div class="metrics-footer"></div>
      </div>
    `;
    messagesViewport.appendChild(row);
    scrollToBottom();

    return {
      card: row.querySelector('.bot-card'),
      contentEl: row.querySelector('.bot-content'),
      metricsEl: row.querySelector('.metrics-footer')
    };
  }

  // Helper: System Announcement
  function appendSystemAnnouncement(text) {
    const div = document.createElement('div');
    div.className = 'system-announcement';
    div.textContent = text;
    messagesViewport.appendChild(div);
    scrollToBottom();
  }

  function scrollToBottom() {
    messagesViewport.scrollTop = messagesViewport.scrollHeight;
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
