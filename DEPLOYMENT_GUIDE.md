# Deployment Guide: Diriyah Brain AI

This guide will walk you through deploying the Diriyah Brain AI Construction Management System to GitHub and Render.

## Prerequisites

- GitHub account
- Render account (free tier available)
- Git installed on your local machine

## Step 1: Push to GitHub

### 1.1 Create a New Repository on GitHub

1. Go to [GitHub](https://github.com) and sign in
2. Click the "+" icon in the top right corner
3. Select "New repository"
4. Name your repository: `diriyah-brain-ai`
5. Make it public or private (your choice)
6. **Do NOT** initialize with README, .gitignore, or license (we already have these)
7. Click "Create repository"

### 1.2 Push Your Code

The code is already initialized as a git repository. To push to GitHub:

```bash
# Add your GitHub repository as remote origin
git remote add origin https://github.com/YOUR_USERNAME/diriyah-brain-ai.git

# Push to GitHub
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

## Step 2: Deploy to Render

### 2.1 Connect GitHub to Render

1. Go to [Render](https://render.com) and sign up/sign in
2. Click "New +" in the top right
3. Select "Web Service"
4. Choose "Build and deploy from a Git repository"
5. Connect your GitHub account if not already connected
6. Select your `diriyah-brain-ai` repository

### 2.2 Configure the Web Service

Fill in the deployment settings:

**Basic Settings:**
- **Name**: `diriyah-brain-ai`
- **Region**: Choose the closest to your users
- **Branch**: `main`
- **Root Directory**: Leave empty (uses repository root)

**Build & Deploy:**
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`

**Advanced Settings:**
- **Auto-Deploy**: `Yes` (recommended)

### 2.3 Set Environment Variables

In the Render dashboard, go to your service and add these environment variables:

**Required:**
- `DATABASE_URL`: `sqlite:///diriyah.db`

**Optional (for full functionality):**
- `OPENAI_API_KEY`: Your OpenAI API key
- `TEAMS_API_KEY`: Microsoft Teams API key
- `WHATSAPP_TOKEN`: WhatsApp Business API token
- `ACONEX_API_KEY`: Aconex API key
- `P6_API_KEY`: Primavera P6 API key
- `POWERBI_API_KEY`: PowerBI API key

**Note**: The application will work without these API keys using mock data for testing.

### 2.4 Deploy

1. Click "Create Web Service"
2. Render will automatically start building and deploying your application
3. The build process typically takes 2-5 minutes
3. Once complete, you'll get a public URL like: `https://diriyah-ai-demo.onrender.com`

## Step 3: Verify Deployment

### 3.1 Test the Application

1. Visit your Render URL
2. Check that the React frontend loads properly
3. Test the AI chat functionality (will use mock responses without OpenAI API key)
4. Verify project switching works
5. Test file upload functionality
6. Try exporting PDF and Excel reports

### 3.2 Monitor Logs

In the Render dashboard:
1. Go to your service
2. Click on "Logs" tab
3. Monitor for any errors or issues

## Step 4: Custom Domain (Optional)

If you want to use a custom domain:

1. In Render dashboard, go to your service
2. Click "Settings" tab
3. Scroll to "Custom Domains"
4. Add your domain
5. Configure DNS records as instructed by Render

## Troubleshooting

### Common Issues

**Build Fails:**
- Check that `requirements.txt` is in the root directory
- Verify all dependencies are correctly listed
- Check build logs for specific error messages

**Application Won't Start:**
- Verify the start command is `python main.py`
- Check that port 8080 is used (Render expects this)
- Review application logs for startup errors

**Frontend Not Loading:**
- Ensure the React build files are in `diriyah_brain_ai/static/`
- Check that the main route serves the React app

**Database Issues:**
- SQLite works for development but consider PostgreSQL for production
- Render provides free PostgreSQL databases

### Performance Optimization

**For Production Use:**

1. **Database**: Upgrade to PostgreSQL
   ```bash
   # Add to requirements.txt
   psycopg2-binary==2.9.7
   
   # Update DATABASE_URL environment variable
   DATABASE_URL=postgresql://user:password@host:port/database
   ```

2. **Caching**: Implement Redis for session management
3. **CDN**: Use Render's CDN for static assets
4. **Monitoring**: Set up health checks and alerts

## Maintenance

### Updating the Application

1. Make changes to your code locally
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Your update message"
   git push origin main
   ```
3. Render will automatically redeploy (if auto-deploy is enabled)

### Monitoring

- Check Render dashboard regularly for service health
- Monitor application logs for errors
- Set up alerts for downtime or errors

### Backup

- Regularly backup your database
- Keep your code in version control (GitHub)
- Document any manual configuration changes

## Security Considerations

1. **Environment Variables**: Never commit API keys to GitHub
2. **HTTPS**: Render provides HTTPS by default
3. **CORS**: Configure CORS settings for production
4. **Authentication**: Implement proper user authentication for production use
5. **Rate Limiting**: Add rate limiting for API endpoints

## Cost Optimization

**Render Free Tier:**
- 750 hours/month of runtime
- Automatic sleep after 15 minutes of inactivity
- Suitable for development and testing

**Paid Plans:**
- Always-on services
- Better performance
- Custom domains
- Priority support

## Next Steps

1. **Add Real API Integrations**: Replace mock data with real API calls
2. **Implement Authentication**: Add user login and role-based access
3. **Database Migration**: Move to PostgreSQL for production
4. **Monitoring**: Set up application monitoring and alerts
5. **Testing**: Implement automated testing
6. **Documentation**: Create user documentation and API docs

## Support

If you encounter issues:

1. Check Render's documentation: https://render.com/docs
2. Review application logs in Render dashboard
3. Check GitHub repository for issues
4. Contact support if needed

Your Diriyah Brain AI application is now live and accessible to users worldwide!

