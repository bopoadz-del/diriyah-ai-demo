// Diriyah Brain AI - Chat Interface JavaScript

let currentProject = 'Heritage Resort';
let chatHistory = [];
let isTyping = false;

// Background services data (simulated)
const backgroundServices = {
    aconex: {
        documents: 1247,
        pending: 23,
        alerts: ['Document review overdue: Foundation specs']
    },
    bim: {
        models: 8,
        lastUpdate: '2024-01-15',
        issues: ['Clash detection: Structural vs MEP in Block A']
    },
    p6: {
        tasks: 342,
        critical: 15,
        delays: ['Foundation work delayed by 3 days']
    },
    powerbi: {
        reports: 12,
        kpis: {
            budget: '75%',
            schedule: '80%',
            quality: '92%'
        }
    }
};

// Project data
const projectData = {
    'Heritage Resort': {
        status: 'Active',
        completion: '78%',
        budget: '75% spent',
        timeline: '5 days behind',
        alerts: [
            'Safety inspection required for Block A foundation',
            'Material delivery delayed for Phase 2',
            'Weather impact on outdoor activities'
        ]
    },
    'Infrastructure MC0A': {
        status: 'Planning',
        completion: '25%',
        budget: '30% allocated',
        timeline: 'On track',
        alerts: ['Environmental approval pending']
    },
    'Residential Complex': {
        status: 'Design',
        completion: '45%',
        budget: '40% spent',
        timeline: '2 days ahead',
        alerts: ['Design review scheduled for next week']
    }
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeChat();
    loadProjectData();
    setupEventListeners();
});

function initializeChat() {
    const chatContainer = document.getElementById('chat-container');
    // Keep the welcome message visible initially
}

function loadProjectData() {
    const project = projectData[currentProject];
    if (project) {
        document.getElementById('current-project').textContent = currentProject;
        updateAlertCount(project.alerts.length);
    }
}

function setupEventListeners() {
    // Project selection
    document.querySelectorAll('.project-item').forEach(item => {
        item.addEventListener('click', function() {
            selectProject(this.dataset.project, this.textContent.trim());
        });
    });
    
    // Chat input
    document.getElementById('chat-input').addEventListener('keypress', handleKeyPress);
    
    // Click outside to close attach menu
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.attach-btn') && !e.target.closest('.attach-menu')) {
            hideAttachMenu();
        }
    });
}

function selectProject(projectKey, projectName) {
    // Update active project
    document.querySelectorAll('.project-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-project="${projectKey}"]`).classList.add('active');
    
    currentProject = projectName;
    document.getElementById('current-project').textContent = projectName;
    
    // Update project data
    loadProjectData();
    
    // Add system message about project switch
    addMessage('system', `Switched to ${projectName}. How can I help you with this project?`);
}

function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message || isTyping) return;
    
    // Add user message
    addMessage('user', message);
    input.value = '';
    
    // Show typing indicator
    showTypingIndicator();
    
    // Process message and get AI response
    setTimeout(() => {
        processMessage(message);
    }, 1000 + Math.random() * 1000);
}

function sendQuickMessage(message) {
    document.getElementById('chat-input').value = message;
    sendMessage();
}

function addMessage(sender, content, timestamp = null) {
    const chatContainer = document.getElementById('chat-container');
    
    // Remove welcome message if it exists
    const welcomeMessage = chatContainer.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.innerHTML = content;
    
    if (timestamp) {
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = timestamp;
        messageContent.appendChild(timeDiv);
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(messageContent);
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    // Store in history
    chatHistory.push({ sender, content, timestamp: new Date().toISOString() });
}

function showTypingIndicator() {
    isTyping = true;
    const chatContainer = document.getElementById('chat-container');
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message ai typing-message';
    typingDiv.innerHTML = `
        <div class="message-avatar"><i class="fas fa-robot"></i></div>
        <div class="message-content">
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
    `;
    
    chatContainer.appendChild(typingDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function hideTypingIndicator() {
    isTyping = false;
    const typingMessage = document.querySelector('.typing-message');
    if (typingMessage) {
        typingMessage.remove();
    }
}

async function processMessage(message) {
    hideTypingIndicator();
    
    try {
        // Check for contextual information needs
        const context = analyzeMessageContext(message);
        
        // Call the AI API
        const response = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                project: currentProject,
                context: context
            })
        });
        
        const data = await response.json();
        
        // Add AI response
        addMessage('ai', data.response, new Date().toLocaleTimeString());
        
        // Check if we need to show alerts
        if (context.showAlerts) {
            showRelevantAlerts(message);
        }
        
    } catch (error) {
        console.error('Error processing message:', error);
        addMessage('ai', 'Sorry, I encountered an error. Please try again.', new Date().toLocaleTimeString());
    }
}

function analyzeMessageContext(message) {
    const lowerMessage = message.toLowerCase();
    const context = {
        showAlerts: false,
        services: [],
        dataNeeded: []
    };
    
    // Check for service-specific queries
    if (lowerMessage.includes('bim') || lowerMessage.includes('model') || lowerMessage.includes('3d')) {
        context.services.push('bim');
        context.dataNeeded.push('bim_data');
    }
    
    if (lowerMessage.includes('schedule') || lowerMessage.includes('timeline') || lowerMessage.includes('p6')) {
        context.services.push('p6');
        context.dataNeeded.push('schedule_data');
    }
    
    if (lowerMessage.includes('document') || lowerMessage.includes('aconex') || lowerMessage.includes('drawing')) {
        context.services.push('aconex');
        context.dataNeeded.push('document_data');
    }
    
    if (lowerMessage.includes('report') || lowerMessage.includes('dashboard') || lowerMessage.includes('powerbi')) {
        context.services.push('powerbi');
        context.dataNeeded.push('report_data');
    }
    
    // Check for alert triggers
    if (lowerMessage.includes('alert') || lowerMessage.includes('issue') || lowerMessage.includes('problem') || 
        lowerMessage.includes('safety') || lowerMessage.includes('delay')) {
        context.showAlerts = true;
    }
    
    return context;
}

function showRelevantAlerts(message) {
    const project = projectData[currentProject];
    if (project && project.alerts.length > 0) {
        const alertBanner = document.getElementById('alert-banner');
        alertBanner.style.display = 'block';
        
        // Auto-hide after 10 seconds
        setTimeout(() => {
            alertBanner.style.display = 'none';
        }, 10000);
    }
}

function createNewChat() {
    const chatContainer = document.getElementById('chat-container');
    chatContainer.innerHTML = `
        <div class="welcome-message">
            <div class="diriyah-logo">
                <i class="fas fa-building"></i>
            </div>
            <h3>New Chat Started</h3>
            <p>How can I help you with ${currentProject} today?</p>
        </div>
    `;
    chatHistory = [];
}

function createTask(taskType) {
    const taskMessages = {
        inspection: 'I need to schedule a safety inspection for the current project.',
        report: 'Please generate a progress report for this project.',
        alert: 'I want to create a new alert for the team.'
    };
    
    const message = taskMessages[taskType];
    if (message) {
        document.getElementById('chat-input').value = message;
        sendMessage();
    }
}

function toggleAlerts() {
    const alertBanner = document.getElementById('alert-banner');
    if (alertBanner.style.display === 'none' || !alertBanner.style.display) {
        alertBanner.style.display = 'block';
    } else {
        alertBanner.style.display = 'none';
    }
}

function dismissAlert(button) {
    button.closest('.alert-item').remove();
    updateAlertCount();
}

function updateAlertCount(count = null) {
    const alertCountElement = document.querySelector('.alert-count');
    if (count !== null) {
        alertCountElement.textContent = count;
        alertCountElement.style.display = count > 0 ? 'block' : 'none';
    } else {
        const remainingAlerts = document.querySelectorAll('.alert-item').length;
        alertCountElement.textContent = remainingAlerts;
        alertCountElement.style.display = remainingAlerts > 0 ? 'block' : 'none';
    }
}

function showProjectOverview() {
    const project = projectData[currentProject];
    if (project) {
        const overview = `📊 **${currentProject} Overview**

**Status:** ${project.status}
**Completion:** ${project.completion}
**Budget:** ${project.budget}
**Timeline:** ${project.timeline}

**Recent Updates:**
• BIM models: ${backgroundServices.bim.models} active models
• Documents: ${backgroundServices.aconex.documents} total documents
• Tasks: ${backgroundServices.p6.tasks} scheduled tasks
• Quality Score: ${backgroundServices.powerbi.kpis.quality}

How can I help you with this project?`;
        
        addMessage('ai', overview, new Date().toLocaleTimeString());
    }
}

function showAttachMenu() {
    const attachMenu = document.getElementById('attach-menu');
    if (attachMenu.style.display === 'none' || !attachMenu.style.display) {
        attachMenu.style.display = 'block';
    } else {
        attachMenu.style.display = 'none';
    }
}

function hideAttachMenu() {
    const attachMenu = document.getElementById('attach-menu');
    attachMenu.style.display = 'none';
}

function attachFile(fileType) {
    const fileInput = document.getElementById('file-input');
    fileInput.setAttribute('accept', getFileAccept(fileType));
    fileInput.click();
    hideAttachMenu();
}

function getFileAccept(fileType) {
    const accepts = {
        document: '.pdf,.doc,.docx,.txt',
        image: '.jpg,.jpeg,.png,.gif',
        cad: '.dwg,.dxf,.step,.iges',
        bim: '.ifc,.rvt,.nwd'
    };
    return accepts[fileType] || '*';
}

// File upload handler - accepts ANY file type
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
        // Show file upload message
        addMessage('user', `📎 Uploaded: ${file.name} (${formatFileSize(file.size)})`, new Date().toLocaleTimeString());
        
        // Process the file
        processUploadedFile(file);
        
        // Clear the input
        event.target.value = '';
    }
}

// Camera capture
function openCamera() {
    document.getElementById('camera-input').click();
}

function handleCameraCapture(event) {
    const file = event.target.files[0];
    if (file) {
        addMessage('user', `📷 Photo captured: ${file.name}`, new Date().toLocaleTimeString());
        processUploadedFile(file);
        event.target.value = '';
    }
}

// Voice recording
let isRecording = false;
let mediaRecorder;
let audioChunks = [];

function toggleRecording() {
    const micBtn = document.getElementById('mic-btn');
    
    if (!isRecording) {
        startRecording();
        micBtn.classList.add('recording');
        micBtn.title = 'Stop recording';
    } else {
        stopRecording();
        micBtn.classList.remove('recording');
        micBtn.title = 'Voice input';
    }
}

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            isRecording = true;
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            
            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };
            
            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                const audioFile = new File([audioBlob], 'voice-message.wav', { type: 'audio/wav' });
                addMessage('user', '🎤 Voice message recorded', new Date().toLocaleTimeString());
                processUploadedFile(audioFile);
                stream.getTracks().forEach(track => track.stop());
            };
            
            mediaRecorder.start();
        })
        .catch(err => {
            console.error('Error accessing microphone:', err);
            alert('Could not access microphone. Please check permissions.');
        });
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        isRecording = false;
        mediaRecorder.stop();
    }
}

// Process uploaded files
function processUploadedFile(file) {
    // Create FormData for file upload
    const formData = new FormData();
    formData.append('file', file);
    
    // Show processing message
    addMessage('ai', '🔄 Processing file...', new Date().toLocaleTimeString());
    
    // Send to backend for processing
    fetch('/api/enhanced-drive/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            addMessage('ai', `✅ File processed successfully: ${data.analysis}`, new Date().toLocaleTimeString());
        } else {
            addMessage('ai', `❌ Error processing file: ${data.error}`, new Date().toLocaleTimeString());
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        addMessage('ai', '❌ Upload failed. Please try again.', new Date().toLocaleTimeString());
    });
}

// Upload menu functionality
function toggleUploadMenu() {
    const uploadMenu = document.getElementById('upload-menu');
    if (uploadMenu.style.display === 'none' || !uploadMenu.style.display) {
        uploadMenu.style.display = 'block';
    } else {
        uploadMenu.style.display = 'none';
    }
}

// Hide upload menu when clicking outside
document.addEventListener('click', function(e) {
    if (!e.target.closest('.upload-menu-container')) {
        const uploadMenu = document.getElementById('upload-menu');
        uploadMenu.style.display = 'none';
    }
});

// Google Drive connection
function connectGoogleDrive() {
    // Hide upload menu
    document.getElementById('upload-menu').style.display = 'none';
    
    // Add message about connecting
    addMessage('user', '🔗 Connecting to Google Drive...', new Date().toLocaleTimeString());
    
    // Start OAuth flow
    window.location.href = '/api/enhanced-drive/auth';
}

// Bottom sidebar functions - Make them functional
function openSettings() {
    addMessage('ai', '⚙️ **Settings Panel**\n\n🔧 **Available Settings:**\n• Language preferences (English/Arabic)\n• Notification settings\n• Data sync options\n• Privacy controls\n• Theme customization\n\nWhich setting would you like to configure?', new Date().toLocaleTimeString());
}

function openHelp() {
    addMessage('ai', '❓ **Help & Documentation**\n\n📚 **Available Resources:**\n• Getting started guide\n• Feature tutorials\n• Keyboard shortcuts\n• Troubleshooting\n• Video tutorials\n• FAQ section\n\nWhat do you need help with?', new Date().toLocaleTimeString());
}

function goHome() {
    addMessage('ai', '🏠 **Home Dashboard**\n\n📊 **Quick Overview:**\n• Active projects: 3\n• Pending tasks: 15\n• Recent alerts: 2\n• System status: ✅ All systems operational\n\nWould you like to see detailed project metrics?', new Date().toLocaleTimeString());
}

function openSupport() {
    addMessage('ai', '🆘 **Support Center**\n\n💬 **Contact Options:**\n• Live chat support\n• Email: support@diriyah.com\n• Phone: +966-11-XXX-XXXX\n• Submit ticket\n• Schedule callback\n\nHow can our support team help you today?', new Date().toLocaleTimeString());
}

function openProfile() {
    addMessage('ai', '👤 **User Profile**\n\n📋 **Profile Information:**\n• Name: Construction Manager\n• Role: Project Administrator\n• Projects: Heritage Resort, Infrastructure MC0A\n• Last login: Today\n• Permissions: Full access\n\nWould you like to update your profile settings?', new Date().toLocaleTimeString());
}

// Utility function
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Background service monitoring (simulated)
setInterval(() => {
    // Simulate background updates
    if (Math.random() < 0.1) { // 10% chance every 30 seconds
        const updates = [
            'New document uploaded to Aconex',
            'BIM model updated with latest changes',
            'P6 schedule synchronized',
            'PowerBI dashboard refreshed'
        ];
        
        const randomUpdate = updates[Math.floor(Math.random() * updates.length)];
        console.log('Background update:', randomUpdate);
    }
}, 30000);

