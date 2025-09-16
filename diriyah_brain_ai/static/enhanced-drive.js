/**
 * Enhanced Google Drive Integration for Diriyah Brain AI
 * Comprehensive file analysis and management
 */

class EnhancedDriveManager {
    constructor() {
        this.isAuthenticated = false;
        this.scanInProgress = false;
        this.analysisData = {};
        this.init();
    }

    init() {
        this.checkAuthStatus();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Add drive scan button to chat interface
        this.addDriveScanButton();
        
        // Listen for drive-related chat commands
        this.setupChatCommands();
    }

    addDriveScanButton() {
        const chatHeader = document.querySelector('.chat-header .header-actions');
        if (chatHeader) {
            const driveButton = document.createElement('button');
            driveButton.className = 'action-btn drive-btn';
            driveButton.innerHTML = '<i class="fas fa-cloud"></i><span>Drive</span>';
            driveButton.onclick = () => this.showDrivePanel();
            chatHeader.appendChild(driveButton);
        }
    }

    setupChatCommands() {
        // Override sendMessage to handle drive commands
        const originalSendMessage = window.sendMessage;
        window.sendMessage = (message) => {
            if (this.handleDriveCommand(message || document.getElementById('chat-input').value)) {
                return;
            }
            originalSendMessage(message);
        };
    }

    handleDriveCommand(message) {
        const lowerMessage = message.toLowerCase();
        
        if (lowerMessage.includes('scan drive') || lowerMessage.includes('analyze drive')) {
            this.startDriveScan();
            return true;
        }
        
        if (lowerMessage.includes('drive status') || lowerMessage.includes('scan status')) {
            this.showScanStatus();
            return true;
        }
        
        if (lowerMessage.includes('search drive') || lowerMessage.includes('find in drive')) {
            const query = message.replace(/search drive|find in drive/gi, '').trim();
            if (query) {
                this.searchDrive(query);
                return true;
            }
        }
        
        return false;
    }

    async checkAuthStatus() {
        try {
            const response = await fetch('/api/enhanced-drive/statistics');
            if (response.ok) {
                this.isAuthenticated = true;
                this.updateDriveStatus('Connected');
            } else {
                this.isAuthenticated = false;
                this.updateDriveStatus('Not Connected');
            }
        } catch (error) {
            this.isAuthenticated = false;
            this.updateDriveStatus('Error');
        }
    }

    async authenticateDrive() {
        try {
            const response = await fetch('/api/enhanced-drive/auth');
            const data = await response.json();
            
            if (data.auth_url) {
                window.open(data.auth_url, '_blank');
                this.addChatMessage('🔐 Please complete Google Drive authentication in the new window.', 'system');
            }
        } catch (error) {
            this.addChatMessage('❌ Failed to start Google Drive authentication.', 'system');
        }
    }

    async startDriveScan() {
        if (!this.isAuthenticated) {
            this.addChatMessage('🔐 Google Drive not connected. Starting authentication...', 'system');
            await this.authenticateDrive();
            return;
        }

        if (this.scanInProgress) {
            this.addChatMessage('⏳ Drive scan already in progress. Use "drive status" to check progress.', 'system');
            return;
        }

        try {
            this.scanInProgress = true;
            this.addChatMessage('🚀 Starting comprehensive Google Drive scan...', 'system');
            
            const response = await fetch('/api/enhanced-drive/scan-all', {
                method: 'POST'
            });
            
            if (response.ok) {
                this.addChatMessage('✅ Drive scan initiated. This may take several minutes for large drives.', 'system');
                this.monitorScanProgress();
            } else {
                throw new Error('Failed to start scan');
            }
        } catch (error) {
            this.scanInProgress = false;
            this.addChatMessage('❌ Failed to start drive scan: ' + error.message, 'system');
        }
    }

    async monitorScanProgress() {
        const progressInterval = setInterval(async () => {
            try {
                const response = await fetch('/api/enhanced-drive/scan-status');
                const status = await response.json();
                
                if (status.status === 'completed') {
                    clearInterval(progressInterval);
                    this.scanInProgress = false;
                    this.addChatMessage(`✅ Drive scan completed! Analyzed ${status.total} files.`, 'system');
                    this.loadAnalysisData();
                } else if (status.status === 'error') {
                    clearInterval(progressInterval);
                    this.scanInProgress = false;
                    this.addChatMessage('❌ Drive scan failed: ' + status.current_file, 'system');
                } else if (status.status === 'scanning') {
                    const progress = Math.round((status.progress / status.total) * 100);
                    this.updateScanProgress(progress, status.current_file);
                }
            } catch (error) {
                clearInterval(progressInterval);
                this.scanInProgress = false;
            }
        }, 2000);
    }

    updateScanProgress(progress, currentFile) {
        const progressMessage = `📊 Scanning: ${progress}% - ${currentFile}`;
        
        // Update existing progress message or add new one
        const chatContainer = document.getElementById('chat-container');
        const existingProgress = chatContainer.querySelector('.scan-progress');
        
        if (existingProgress) {
            existingProgress.textContent = progressMessage;
        } else {
            this.addChatMessage(progressMessage, 'system', 'scan-progress');
        }
    }

    async showScanStatus() {
        try {
            const response = await fetch('/api/enhanced-drive/scan-status');
            const status = await response.json();
            
            let statusMessage = '';
            if (status.status === 'idle') {
                statusMessage = '💤 No scan in progress. Use "scan drive" to start.';
            } else if (status.status === 'scanning') {
                const progress = Math.round((status.progress / status.total) * 100);
                statusMessage = `⏳ Scanning in progress: ${progress}% (${status.progress}/${status.total})`;
            } else if (status.status === 'completed') {
                statusMessage = `✅ Last scan completed. ${status.total} files analyzed.`;
            } else if (status.status === 'error') {
                statusMessage = `❌ Scan error: ${status.current_file}`;
            }
            
            this.addChatMessage(statusMessage, 'system');
        } catch (error) {
            this.addChatMessage('❌ Failed to get scan status.', 'system');
        }
    }

    async searchDrive(query) {
        try {
            this.addChatMessage(`🔍 Searching drive for: "${query}"`, 'system');
            
            const response = await fetch(`/api/enhanced-drive/search?query=${encodeURIComponent(query)}&limit=10`);
            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                let resultsMessage = `📋 Found ${data.total_results} results (showing top ${data.results.length}):\n\n`;
                
                data.results.forEach((file, index) => {
                    resultsMessage += `${index + 1}. **${file.name}**\n`;
                    resultsMessage += `   Type: ${file.metadata?.file_type || 'Unknown'}\n`;
                    resultsMessage += `   Summary: ${file.content_summary}\n`;
                    if (file.web_link) {
                        resultsMessage += `   [View File](${file.web_link})\n`;
                    }
                    resultsMessage += '\n';
                });
                
                this.addChatMessage(resultsMessage, 'system');
            } else {
                this.addChatMessage(`🔍 No results found for "${query}". Try different keywords.`, 'system');
            }
        } catch (error) {
            this.addChatMessage('❌ Search failed: ' + error.message, 'system');
        }
    }

    async loadAnalysisData() {
        try {
            const response = await fetch('/api/enhanced-drive/statistics');
            const stats = await response.json();
            
            if (stats.total_files) {
                this.analysisData = stats;
                this.showDriveStatistics(stats);
            }
        } catch (error) {
            console.error('Failed to load analysis data:', error);
        }
    }

    showDriveStatistics(stats) {
        let statsMessage = `📊 **Drive Analysis Summary**\n\n`;
        statsMessage += `📁 Total Files: ${stats.total_files}\n`;
        statsMessage += `💾 Total Size: ${stats.total_size_mb} MB\n`;
        statsMessage += `🔗 Shared Files: ${stats.shared_files}\n\n`;
        
        statsMessage += `**File Types:**\n`;
        Object.entries(stats.file_types).forEach(([type, count]) => {
            statsMessage += `• ${type}: ${count}\n`;
        });
        
        statsMessage += `\n**Analysis Status:**\n`;
        Object.entries(stats.analysis_status).forEach(([status, count]) => {
            statsMessage += `• ${status}: ${count}\n`;
        });
        
        this.addChatMessage(statsMessage, 'system');
    }

    showDrivePanel() {
        // Create drive management panel
        const panel = document.createElement('div');
        panel.className = 'drive-panel';
        panel.innerHTML = `
            <div class="drive-panel-content">
                <div class="drive-panel-header">
                    <h3><i class="fas fa-cloud"></i> Google Drive Manager</h3>
                    <button onclick="this.parentElement.parentElement.parentElement.remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="drive-panel-body">
                    <div class="drive-actions">
                        <button onclick="driveManager.startDriveScan()" class="drive-action-btn">
                            <i class="fas fa-sync"></i> Scan Drive
                        </button>
                        <button onclick="driveManager.showScanStatus()" class="drive-action-btn">
                            <i class="fas fa-info"></i> Status
                        </button>
                        <button onclick="driveManager.showFileTypes()" class="drive-action-btn">
                            <i class="fas fa-file"></i> File Types
                        </button>
                        <button onclick="driveManager.showArchives()" class="drive-action-btn">
                            <i class="fas fa-archive"></i> Archives
                        </button>
                    </div>
                    <div class="drive-search">
                        <input type="text" id="drive-search-input" placeholder="Search drive content...">
                        <button onclick="driveManager.searchDrive(document.getElementById('drive-search-input').value)">
                            <i class="fas fa-search"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(panel);
    }

    async showFileTypes() {
        try {
            const response = await fetch('/api/enhanced-drive/statistics');
            const stats = await response.json();
            
            if (stats.file_types) {
                let message = '📂 **File Types in Drive:**\n\n';
                Object.entries(stats.file_types)
                    .sort(([,a], [,b]) => b - a)
                    .forEach(([type, count]) => {
                        message += `• ${type}: ${count} files\n`;
                    });
                
                this.addChatMessage(message, 'system');
            }
        } catch (error) {
            this.addChatMessage('❌ Failed to get file types.', 'system');
        }
    }

    async showArchives() {
        try {
            const response = await fetch('/api/enhanced-drive/archives');
            const data = await response.json();
            
            if (data.archives && data.archives.length > 0) {
                let message = `📦 **Archive Files (${data.total}):**\n\n`;
                
                data.archives.slice(0, 10).forEach((archive, index) => {
                    message += `${index + 1}. **${archive.name}**\n`;
                    message += `   Files: ${archive.metadata?.total_files || 'Unknown'}\n`;
                    message += `   Types: ${Object.keys(archive.metadata?.file_types || {}).join(', ')}\n\n`;
                });
                
                if (data.total > 10) {
                    message += `... and ${data.total - 10} more archives\n`;
                }
                
                this.addChatMessage(message, 'system');
            } else {
                this.addChatMessage('📦 No archive files found in drive.', 'system');
            }
        } catch (error) {
            this.addChatMessage('❌ Failed to get archives.', 'system');
        }
    }

    updateDriveStatus(status) {
        // Update UI to show drive connection status
        const driveBtn = document.querySelector('.drive-btn');
        if (driveBtn) {
            driveBtn.title = `Google Drive: ${status}`;
            if (status === 'Connected') {
                driveBtn.classList.add('connected');
            } else {
                driveBtn.classList.remove('connected');
            }
        }
    }

    addChatMessage(message, type = 'system', className = '') {
        const chatContainer = document.getElementById('chat-container');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message ${className}`;
        
        // Convert markdown-style formatting to HTML
        const formattedMessage = message
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n/g, '<br>');
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-text">${formattedMessage}</div>
                <div class="message-time">${new Date().toLocaleTimeString()}</div>
            </div>
        `;
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

// Initialize enhanced drive manager
const driveManager = new EnhancedDriveManager();

// Add CSS for drive panel
const driveStyles = `
.drive-panel {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    z-index: 2000;
    min-width: 400px;
    max-width: 90vw;
}

.drive-panel-content {
    padding: 0;
}

.drive-panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    border-bottom: 1px solid var(--border-color);
    background: var(--diriyah-primary);
    color: white;
    border-radius: 12px 12px 0 0;
}

.drive-panel-header h3 {
    margin: 0;
    display: flex;
    align-items: center;
    gap: 10px;
}

.drive-panel-header button {
    background: none;
    border: none;
    color: white;
    font-size: 18px;
    cursor: pointer;
    padding: 5px;
    border-radius: 4px;
}

.drive-panel-header button:hover {
    background: rgba(255,255,255,0.2);
}

.drive-panel-body {
    padding: 20px;
}

.drive-actions {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 10px;
    margin-bottom: 20px;
}

.drive-action-btn {
    padding: 12px;
    background: var(--diriyah-light);
    border: 1px solid var(--diriyah-primary);
    border-radius: 8px;
    color: var(--diriyah-primary);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    transition: all 0.3s ease;
}

.drive-action-btn:hover {
    background: var(--diriyah-primary);
    color: white;
}

.drive-action-btn i {
    font-size: 16px;
}

.drive-search {
    display: flex;
    gap: 10px;
}

.drive-search input {
    flex: 1;
    padding: 10px;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    background: var(--bg-secondary);
    color: var(--text-primary);
}

.drive-search button {
    padding: 10px 15px;
    background: var(--diriyah-primary);
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
}

.drive-btn.connected {
    background: var(--success-color);
    color: white;
}

.system-message {
    background: var(--bg-secondary);
    border-left: 4px solid var(--diriyah-primary);
    margin: 10px 0;
    padding: 10px;
    border-radius: 0 8px 8px 0;
}

.scan-progress {
    font-family: monospace;
    color: var(--diriyah-primary);
}
`;

// Add styles to document
const styleSheet = document.createElement('style');
styleSheet.textContent = driveStyles;
document.head.appendChild(styleSheet);

