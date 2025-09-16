# Diriyah Brain AI - Construction Project Management System

A comprehensive construction project management system with AI support, featuring real-time data integration, intelligent analytics, and modern web interface.

## Features

- **AI-Powered Assistant**: Chat with an AI assistant for project insights and recommendations
- **Project Dashboard**: Real-time project metrics, alerts, and status tracking
- **File Management**: Integration with Google Drive for document management
- **Quality Analysis**: AI-powered photo analysis for construction site safety and compliance
- **Multi-Platform Integration**: Support for WhatsApp, Microsoft Teams, Aconex, P6, and PowerBI
- **Export Capabilities**: Generate PDF reports and Excel spreadsheets
- **Modern UI**: Responsive React frontend with Tailwind CSS and shadcn/ui components

## Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLite**: Lightweight database for development
- **OpenAI API**: AI chat functionality
- **Pillow**: Image processing
- **ReportLab**: PDF generation
- **OpenPyXL**: Excel file generation

### Frontend
- **React**: Modern JavaScript framework
- **Vite**: Fast build tool
- **Tailwind CSS**: Utility-first CSS framework
- **shadcn/ui**: High-quality React components
- **Lucide Icons**: Beautiful icon library

## Project Structure

```
diriyah-ai-demo/
├── main.py                     # FastAPI application entry point
├── requirements.txt            # Python dependencies
├── .env                       # Environment variables
├── render.yaml                # Render deployment configuration
├── diriyah_brain_ai/          # Backend modules
│   ├── config.py              # Configuration settings
│   ├── db_init.py             # Database initialization
│   ├── schemas.py             # Pydantic models
│   ├── drive_adapter.py       # Google Drive integration
│   ├── routers/               # API route modules
│   │   ├── projects.py        # Project management routes
│   │   ├── ai.py              # AI chat routes
│   │   ├── integrations.py    # WhatsApp/Teams integration
│   │   ├── drive.py           # Google Drive routes
│   │   └── mock_data.py       # Mock data for testing
│   └── static/                # Static files and built frontend
├── diriyah-frontend/          # React frontend source
│   ├── src/
│   │   ├── App.jsx            # Main React component
│   │   ├── App.css            # Styles
│   │   └── components/        # UI components
│   ├── package.json           # Node.js dependencies
│   └── vite.config.js         # Vite configuration
└── uploads/                   # File upload directory
```

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- pnpm (recommended) or npm

### Backend Setup
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. Run the backend server:
   ```bash
   python main.py
   ```
   The API will be available at `http://localhost:8080`

### Frontend Development
1. Navigate to the frontend directory:
   ```bash
   cd diriyah-frontend
   ```

2. Install dependencies:
   ```bash
   pnpm install
   ```

3. Start the development server:
   ```bash
   pnpm run dev
   ```
   The frontend will be available at `http://localhost:5173`

### Building for Production
1. Build the React frontend:
   ```bash
   cd diriyah-frontend
   pnpm run build
   ```

2. Copy built files to backend static directory:
   ```bash
   cp -r diriyah-frontend/dist/* diriyah_brain_ai/static/
   ```

## Deployment

### GitHub Setup
1. Initialize git repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. Create a new repository on GitHub and push:
   ```bash
   git remote add origin https://github.com/yourusername/diriyah-brain-ai.git
   git branch -M main
   git push -u origin main
   ```

### Render Deployment
1. Connect your GitHub repository to Render
2. Use the provided `render.yaml` configuration
3. Set environment variables in Render dashboard:
   - `OPENAI_API_KEY`: Your OpenAI API key (optional for testing)
   - Other API keys as needed

### Environment Variables
- `OPENAI_API_KEY`: OpenAI API key for AI chat functionality
- `DATABASE_URL`: Database connection string (SQLite for development)
- `TEAMS_API_KEY`: Microsoft Teams API key
- `WHATSAPP_TOKEN`: WhatsApp Business API token
- `ACONEX_API_KEY`: Aconex API key
- `P6_API_KEY`: Primavera P6 API key
- `POWERBI_API_KEY`: PowerBI API key
- `YOLO_MODEL_PATH`: Path to YOLO model for image analysis

## API Documentation

Once the server is running, visit `http://localhost:8080/docs` for interactive API documentation.

### Key Endpoints
- `GET /projects/list`: List all projects
- `POST /api/ai/chat`: Chat with AI assistant
- `GET /drive/files`: Get project files from Google Drive
- `POST /quality/photo`: Analyze construction photos
- `GET /export/pdf`: Export project report as PDF
- `GET /export/excel`: Export alerts as Excel file

## Features in Detail

### AI Assistant
The AI assistant provides intelligent responses to project-related queries. It can help with:
- Project status inquiries
- Risk assessment
- Resource planning recommendations
- Technical guidance

### Google Drive Integration
The system integrates with Google Drive to:
- List project files
- Search documents
- Provide centralized file access
- Maintain project documentation

### Quality Analysis
Upload construction site photos for AI-powered analysis:
- Safety compliance checking
- Object detection (workers, equipment, safety gear)
- Automated reporting
- Visual documentation

### Multi-Platform Integration
Connect with various construction industry tools:
- **WhatsApp**: Team communication and notifications
- **Microsoft Teams**: Corporate communication
- **Aconex**: Document management and correspondence
- **Primavera P6**: Project scheduling and milestones
- **PowerBI**: Advanced analytics and reporting

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and commit: `git commit -m "Add feature"`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue on GitHub or contact the development team.


