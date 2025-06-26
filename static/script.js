class CMUAfricaChatbot {
    constructor() {
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendButton = document.getElementById('sendButton');
        this.inputWrapper = document.getElementById('inputWrapper');
        this.typingIndicator = document.getElementById('typingIndicator');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        
        this.isTyping = false;
        this.conversationHistory = [];
        this.apiBaseUrl = 'http://localhost:5000/api'; // Backend API URL
        this.systemReady = false;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupTextareaAutoResize();
        this.checkSystemStatus();
        this.startStatusPolling();
    }
    
    setupEventListeners() {
        this.sendButton.addEventListener('click', () => this.handleSend());
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSend();
            }
        });
        
        this.chatInput.addEventListener('focus', () => {
            this.inputWrapper.classList.add('focused');
        });
        
        this.chatInput.addEventListener('blur', () => {
            this.inputWrapper.classList.remove('focused');
        });
    }
    
    setupTextareaAutoResize() {
        this.chatInput.addEventListener('input', () => {
            this.chatInput.style.height = 'auto';
            this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 120) + 'px';
        });
    }
    
    updateStatus(status, message = '') {
        const indicator = this.statusIndicator;
        switch(status) {
            case 'ready':
                indicator.style.background = '#27ae60';
                this.statusText.innerHTML = 'Online';
                this.systemReady = true;
                break;
            case 'initializing':
                indicator.style.background = '#f39c12';
                this.statusText.innerHTML = message || 'Initializing system...';
                this.systemReady = false;
                break;
            case 'thinking':
                indicator.style.background = '#3498db';
                this.statusText.innerHTML = 'Processing your question...';
                break;
            case 'error':
                indicator.style.background = '#e74c3c';
                this.statusText.innerHTML = message || 'Something went wrong';
                this.systemReady = false;
                break;
        }
    }
    
    async checkSystemStatus() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/status`);
            const data = await response.json();
            
            if (data.status === 'ready') {
                this.updateStatus('ready');
            } else if (data.status === 'initializing') {
                this.updateStatus('initializing', data.message);
            } else if (data.status === 'error') {
                this.updateStatus('error', data.message);
                this.showSystemError(data.message);
            }
        } catch (error) {
            console.error('Failed to check system status:', error);
            this.updateStatus('error', 'Cannot connect to backend');
            this.showSystemError('Cannot connect to the backend server.');
        }
    }
    
    startStatusPolling() {
        // Poll status every 3 seconds until system is ready
        const pollInterval = setInterval(async () => {
            if (!this.systemReady) {
                await this.checkSystemStatus();
            } else {
                clearInterval(pollInterval);
            }
        }, 3000);
    }
    
    showSystemError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <strong>⚠️ System Error:</strong><br>
            ${message}<br><br>
            <small>Please make sure the backend is running and try refreshing the page.</small>
        `;
        
        // Insert at the top of chat messages
        this.chatMessages.insertBefore(errorDiv, this.chatMessages.firstChild);
    }
    
    async handleSend() {
        const message = this.chatInput.value.trim();
        if (!message || this.isTyping) return;
        
        if (!this.systemReady) {
            this.addMessage('System is still initializing. Please wait a moment and try again.', 'bot');
            return;
        }
        
        this.addMessage(message, 'user');
        this.chatInput.value = '';
        this.chatInput.style.height = 'auto';
        
        this.setTyping(true);
        this.updateStatus('thinking');
        
        try {
            const response = await this.getAIResponse(message);
            
            if (response.error) {
                this.addMessage(`Sorry, I encountered an error: ${response.error}`, 'bot');
                this.updateStatus('error');
                setTimeout(() => this.updateStatus('ready'), 3000);
            } else {
                this.addMessage(response.answer, 'bot', response.sources);
                this.updateStatus('ready');
            }
        } catch (error) {
            console.error('Error:', error);
            this.addMessage('I apologize, but I encountered an error processing your question. Please check if the backend server is running and try again.', 'bot');
            this.updateStatus('error');
            setTimeout(() => this.updateStatus('ready'), 3000);
        }
        
        this.setTyping(false);
    }
    
    async getAIResponse(message) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            return data;
            
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }
    
    // Helper method to clear conversation memory on backend
    async clearMemory() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/clear-memory`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (response.ok) {
                console.log('Memory cleared successfully');
            }
        } catch (error) {
            console.error('Failed to clear memory:', error);
        }
    }
    
    addMessage(content, sender, sources = []) {
        // Remove welcome message if it exists
        const welcomeMsg = this.chatMessages.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = sender === 'user' ? '👤' : '🤖';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // Handle markdown-like formatting
        const formattedContent = this.formatMessage(content);
        messageContent.innerHTML = formattedContent;
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        // Add sources if available
        if (sources && sources.length > 0) {
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'sources';
            sourcesDiv.innerHTML = `<h4>📚 Sources:</h4>`;

            const orderedList = document.createElement('ol'); // Create an ordered list

            // source have url only
            sources.forEach(source => {
                const listItem = document.createElement('li');
                listItem.innerHTML = `<a href="${source}" target="_blank">${source}</a>`;
                orderedList.appendChild(listItem);
            });

            sourcesDiv.appendChild(orderedList);
            messageContent.appendChild(sourcesDiv);
        }

        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Store in conversation history
        this.conversationHistory.push({
            content,
            sender,
            timestamp: new Date(),
            sources
        });
    }
    
    formatMessage(content) {
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Bold text
            .replace(/\*(.*?)\*/g, '<em>$1</em>')              // Italic text
            .replace(/\n/g, '<br>')                           // Line breaks
            .replace(/•/g, '•');                              // Bullet points
    }
    
    setTyping(isTyping) {
        this.isTyping = isTyping;
        this.sendButton.disabled = isTyping;
        this.typingIndicator.style.display = isTyping ? 'flex' : 'none';
        
        if (isTyping) {
            this.scrollToBottom();
        }
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
}

// Initialize the chatbot when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new CMUAfricaChatbot();
});

// copy li content to the textarea when clicked
document.querySelectorAll('.faq-intro-message li').forEach(item => {
    item.addEventListener('click', () => {
        const question = item.textContent.replace(/🔍/g, '').trim();
        const chatInput = document.getElementById('chatInput');
        chatInput.value = question;
        chatInput.focus();
        chatInput.dispatchEvent(new Event('input')); // Trigger auto-resize
    });
});
