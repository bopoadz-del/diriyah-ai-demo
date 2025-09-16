// Diriyah Brain AI - Construction Management System JavaScript

// Global variables
let currentProject = 'Heritage Resort';
let currentLanguage = 'en';
let isArabic = false;

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    loadProjects();
    loadAlerts();
    loadFiles();
    loadAconexData();
    loadP6Data();
    loadPowerBIData();
    setupEventListeners();
});

// Initialize application
function initializeApp() {
    console.log('Initializing Diriyah Brain AI...');
    updateProjectName();
}

// Setup event listeners
function setupEventListeners() {
    // Chat functionality
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-chat-btn');
    
    if (chatInput && sendButton) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendChatMessage();
            }
        });
        
        sendButton.addEventListener('click', sendChatMessage);
    }
    
    // Language toggle
    const langToggle = document.getElementById('lang-toggle-btn');
    if (langToggle) {
        langToggle.addEventListener('click', toggleLanguage);
    }
    
    // Export buttons
    const exportPdfBtn = document.getElementById('export-pdf-btn');
    const exportExcelBtn = document.getElementById('export-excel-btn');
    
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', exportPDF);
    }
    
    if (exportExcelBtn) {
        exportExcelBtn.addEventListener('click', exportExcel);
    }
    
    // File upload
    const fileUploadBtn = document.getElementById('file-upload-btn');
    if (fileUploadBtn) {
        fileUploadBtn.addEventListener('click', uploadFile);
    }
    
    // Photo analysis
    const photoAnalysisBtn = document.getElementById('photo-analysis-btn');
    if (photoAnalysisBtn) {
        photoAnalysisBtn.addEventListener('click', analyzePhoto);
    }
}

// Chat functionality
async function sendChatMessage() {
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    
    if (!chatInput || !chatMessages) return;
    
    const message = chatInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addChatMessage(message, 'user');
    chatInput.value = '';
    
    // Show loading indicator
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'chat-message ai loading-message';
    loadingDiv.innerHTML = '<div class="loading"></div> Thinking...';
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    try {
        // Send message to AI endpoint
        const response = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                project: currentProject,
                language: currentLanguage
            })
        });
        
        // Remove loading indicator
        chatMessages.removeChild(loadingDiv);
        
        if (response.ok) {
            const data = await response.json();
            addChatMessage(data.response, 'ai');
        } else {
            addChatMessage('Sorry, I encountered an error. Please try again.', 'ai');
        }
    } catch (error) {
        console.error('Chat error:', error);
        chatMessages.removeChild(loadingDiv);
        addChatMessage('Sorry, I encountered a connection error. Please try again.', 'ai');
    }
}

function addChatMessage(message, sender) {
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${sender}`;
    messageDiv.textContent = message;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Language toggle functionality
function toggleLanguage() {
    isArabic = !isArabic;
    currentLanguage = isArabic ? 'ar' : 'en';
    
    document.body.classList.toggle('rtl', isArabic);
    
    // Update UI text based on language
    updateUILanguage();
}

function updateUILanguage() {
    const translations = {
        en: {
            dashboard: 'Dashboard',
            projects: 'Projects',
            reports: 'Reports',
            settings: 'Settings',
            welcome: 'Welcome to',
            projectOverview: 'Project Overview',
            recentAlerts: 'Recent Alerts',
            driveFiles: 'Drive Files',
            uploadNewFile: 'Upload New File',
            qualityPhotoAnalysis: 'Quality Photo Analysis',
            aconexCorrespondence: 'Aconex Correspondence',
            p6Milestones: 'P6 Milestones',
            powerbiSummary: 'PowerBI Summary',
            aiAssistant: 'AI Assistant',
            askAnything: 'Ask me anything...'
        },
        ar: {
            dashboard: 'لوحة التحكم',
            projects: 'المشاريع',
            reports: 'التقارير',
            settings: 'الإعدادات',
            welcome: 'مرحباً بك في',
            projectOverview: 'نظرة عامة على المشروع',
            recentAlerts: 'التنبيهات الحديثة',
            driveFiles: 'ملفات التخزين',
            uploadNewFile: 'رفع ملف جديد',
            qualityPhotoAnalysis: 'تحليل صور الجودة',
            aconexCorrespondence: 'مراسلات أكونكس',
            p6Milestones: 'معالم P6',
            powerbiSummary: 'ملخص PowerBI',
            aiAssistant: 'المساعد الذكي',
            askAnything: 'اسأل أي شيء...'
        }
    };
    
    const t = translations[currentLanguage];
    
    // Update navigation
    const navItems = document.querySelectorAll('.nav-item');
    if (navItems.length >= 4) {
        navItems[0].textContent = t.dashboard;
        navItems[1].textContent = t.projects;
        navItems[2].textContent = t.reports;
        navItems[3].textContent = t.settings;
    }
    
    // Update chat placeholder
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.placeholder = t.askAnything;
    }
    
    // Update chat header
    const chatHeader = document.querySelector('.chat-header');
    if (chatHeader) {
        chatHeader.textContent = t.aiAssistant;
    }
}

// Load projects
async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        if (response.ok) {
            const projects = await response.json();
            displayProjects(projects);
        }
    } catch (error) {
        console.error('Error loading projects:', error);
        // Fallback to mock data
        displayProjects([
            { id: 1, name: 'Heritage Resort', status: 'active' },
            { id: 2, name: 'Diriyah Gate', status: 'planning' },
            { id: 3, name: 'Cultural District', status: 'active' }
        ]);
    }
}

function displayProjects(projects) {
    const projectList = document.getElementById('project-list');
    if (!projectList) return;
    
    projectList.innerHTML = '';
    
    projects.forEach(project => {
        const projectDiv = document.createElement('div');
        projectDiv.className = 'sidebar-item';
        if (project.name === currentProject) {
            projectDiv.classList.add('active');
        }
        projectDiv.textContent = project.name;
        projectDiv.addEventListener('click', () => selectProject(project.name));
        projectList.appendChild(projectDiv);
    });
}

function selectProject(projectName) {
    currentProject = projectName;
    updateProjectName();
    
    // Update active project in sidebar
    const projectItems = document.querySelectorAll('#project-list .sidebar-item');
    projectItems.forEach(item => {
        item.classList.toggle('active', item.textContent === projectName);
    });
    
    // Reload data for new project
    loadAlerts();
    loadFiles();
}

function updateProjectName() {
    const projectNameElement = document.getElementById('current-project-name');
    if (projectNameElement) {
        projectNameElement.textContent = currentProject;
    }
}

// Load alerts
async function loadAlerts() {
    try {
        const response = await fetch(`/api/alerts?project=${encodeURIComponent(currentProject)}`);
        if (response.ok) {
            const alerts = await response.json();
            displayAlerts(alerts);
        }
    } catch (error) {
        console.error('Error loading alerts:', error);
        // Fallback to mock data
        displayAlerts([
            { id: 1, type: 'high', message: 'Concrete strength test failed - NCR #45', timestamp: '2024-09-15T10:30:00Z' },
            { id: 2, type: 'medium', message: 'RFI #234 pending response from consultant', timestamp: '2024-09-15T09:15:00Z' },
            { id: 3, type: 'low', message: 'Material delivery scheduled for tomorrow', timestamp: '2024-09-15T08:00:00Z' }
        ]);
    }
}

function displayAlerts(alerts) {
    const alertsGrid = document.getElementById('alerts-grid');
    if (!alertsGrid) return;
    
    alertsGrid.innerHTML = '';
    
    alerts.forEach(alert => {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert-item ${alert.type}`;
        alertDiv.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 0.5rem;">${alert.type.toUpperCase()} PRIORITY</div>
            <div>${alert.message}</div>
            <div style="font-size: 0.8rem; color: #666; margin-top: 0.5rem;">
                ${new Date(alert.timestamp).toLocaleString()}
            </div>
        `;
        alertsGrid.appendChild(alertDiv);
    });
}

// Load files
async function loadFiles() {
    try {
        const response = await fetch(`/api/drive/files?project=${encodeURIComponent(currentProject)}`);
        if (response.ok) {
            const files = await response.json();
            displayFiles(files);
        }
    } catch (error) {
        console.error('Error loading files:', error);
        // Fallback to mock data
        displayFiles([
            { name: 'BOQ_Heritage_Resort.xlsx', type: 'excel', size: '2.5 MB' },
            { name: 'Schedule_P6.xml', type: 'xml', size: '1.8 MB' },
            { name: 'Site_Photos_Sept.zip', type: 'archive', size: '15.2 MB' },
            { name: 'NCR_045.pdf', type: 'pdf', size: '0.8 MB' }
        ]);
    }
}

function displayFiles(files) {
    const fileGrid = document.getElementById('file-grid');
    if (!fileGrid) return;
    
    fileGrid.innerHTML = '';
    
    files.forEach(file => {
        const fileDiv = document.createElement('div');
        fileDiv.className = 'file-item';
        
        const iconClass = getFileIcon(file.type);
        
        fileDiv.innerHTML = `
            <div class="file-icon"><i class="${iconClass}"></i></div>
            <div style="font-weight: bold; margin-bottom: 0.5rem;">${file.name}</div>
            <div style="font-size: 0.8rem; color: #666;">${file.size}</div>
        `;
        
        fileDiv.addEventListener('click', () => openFile(file));
        fileGrid.appendChild(fileDiv);
    });
}

function getFileIcon(fileType) {
    const icons = {
        pdf: 'fas fa-file-pdf',
        excel: 'fas fa-file-excel',
        word: 'fas fa-file-word',
        image: 'fas fa-file-image',
        archive: 'fas fa-file-archive',
        xml: 'fas fa-file-code',
        default: 'fas fa-file'
    };
    
    return icons[fileType] || icons.default;
}

function openFile(file) {
    console.log('Opening file:', file.name);
    // Implement file opening logic
}

// Load Aconex data
async function loadAconexData() {
    try {
        const response = await fetch(`/api/aconex?project=${encodeURIComponent(currentProject)}`);
        if (response.ok) {
            const data = await response.json();
            displayAconexData(data);
        }
    } catch (error) {
        console.error('Error loading Aconex data:', error);
        displayAconexData({ status: 'No Aconex integration available' });
    }
}

function displayAconexData(data) {
    const aconexContent = document.getElementById('aconex-content');
    if (!aconexContent) return;
    
    aconexContent.innerHTML = `<p>${data.status || 'Loading Aconex correspondence...'}</p>`;
}

// Load P6 data
async function loadP6Data() {
    try {
        const response = await fetch(`/api/p6?project=${encodeURIComponent(currentProject)}`);
        if (response.ok) {
            const data = await response.json();
            displayP6Data(data);
        }
    } catch (error) {
        console.error('Error loading P6 data:', error);
        displayP6Data({ status: 'No P6 integration available' });
    }
}

function displayP6Data(data) {
    const p6Content = document.getElementById('p6-content');
    if (!p6Content) return;
    
    p6Content.innerHTML = `<p>${data.status || 'Loading P6 milestones...'}</p>`;
}

// Load PowerBI data
async function loadPowerBIData() {
    try {
        const response = await fetch(`/api/powerbi?project=${encodeURIComponent(currentProject)}`);
        if (response.ok) {
            const data = await response.json();
            displayPowerBIData(data);
        }
    } catch (error) {
        console.error('Error loading PowerBI data:', error);
        displayPowerBIData({ status: 'No PowerBI integration available' });
    }
}

function displayPowerBIData(data) {
    const powerbiContent = document.getElementById('powerbi-summary');
    if (!powerbiContent) return;
    
    const contentDiv = powerbiContent.querySelector('div') || document.createElement('div');
    contentDiv.innerHTML = `<p>${data.status || 'Loading PowerBI summary...'}</p>`;
    
    if (!powerbiContent.querySelector('div')) {
        powerbiContent.appendChild(contentDiv);
    }
}

// Export functions
async function exportPDF() {
    try {
        const response = await fetch('/api/export/pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                project: currentProject,
                language: currentLanguage
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentProject}_Report.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            alert('Error exporting PDF');
        }
    } catch (error) {
        console.error('Export PDF error:', error);
        alert('Error exporting PDF');
    }
}

async function exportExcel() {
    try {
        const response = await fetch('/api/export/excel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                project: currentProject,
                language: currentLanguage
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentProject}_Alerts.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            alert('Error exporting Excel');
        }
    } catch (error) {
        console.error('Export Excel error:', error);
        alert('Error exporting Excel');
    }
}

// File upload
async function uploadFile() {
    const fileInput = document.getElementById('file-upload-input');
    if (!fileInput || !fileInput.files[0]) {
        alert('Please select a file to upload');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('project', currentProject);
    
    try {
        const response = await fetch('/api/drive/upload', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            alert('File uploaded successfully');
            fileInput.value = '';
            loadFiles(); // Reload file list
        } else {
            alert('Error uploading file');
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('Error uploading file');
    }
}

// Photo analysis
async function analyzePhoto() {
    const photoInput = document.getElementById('photo-analysis-input');
    const resultDiv = document.getElementById('analysis-result');
    
    if (!photoInput || !photoInput.files[0]) {
        alert('Please select a photo to analyze');
        return;
    }
    
    const formData = new FormData();
    formData.append('photo', photoInput.files[0]);
    formData.append('project', currentProject);
    
    resultDiv.innerHTML = '<div class="loading"></div> Analyzing photo...';
    
    try {
        const response = await fetch('/api/quality/analyze-photo', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            resultDiv.innerHTML = `
                <h4>Analysis Result:</h4>
                <p>${result.analysis || 'Photo analysis completed'}</p>
                <p><strong>Quality Score:</strong> ${result.quality_score || 'N/A'}</p>
                <p><strong>Issues Found:</strong> ${result.issues_count || 0}</p>
            `;
        } else {
            resultDiv.innerHTML = '<p>Error analyzing photo</p>';
        }
    } catch (error) {
        console.error('Photo analysis error:', error);
        resultDiv.innerHTML = '<p>Error analyzing photo</p>';
    }
}

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#dc3545' : '#28a745'};
        color: white;
        padding: 1rem;
        border-radius: 5px;
        z-index: 1000;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    `;
    
    document.body.appendChild(notification);
    
    // Remove notification after 3 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 3000);
}

// Error handling
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
});

// Service worker registration (for offline functionality)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(err) {
                console.log('ServiceWorker registration failed');
            });
    });
}

