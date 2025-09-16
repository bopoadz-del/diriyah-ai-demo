# Google Drive API Setup Guide

## Overview

This guide will help you set up Google Drive API integration for the Diriyah Brain AI system using your existing Render deployment at `diriyah-ai-demo.onrender.com`.

## Step 1: Google Cloud Console Setup

### 1.1 Create/Select Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Name it something like "Diriyah Brain AI" or "Construction Management"

### 1.2 Enable Google Drive API
1. In the Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google Drive API"
3. Click on it and press "Enable"

### 1.3 Create OAuth 2.0 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client ID"
3. If prompted, configure the OAuth consent screen first:
   - Choose "External" user type
   - Fill in application name: "Diriyah Brain AI"
   - Add your email as developer contact
   - Add scopes: `../auth/drive.readonly` and `../auth/drive.file`

### 1.4 Configure OAuth Client
**Application Type:** Web application

**Name:** Diriyah Brain AI Web Client

**Authorized JavaScript Origins:**
```
https://diriyah-ai-demo.onrender.com
http://localhost:8080
```

**Authorized Redirect URIs:**
```
https://diriyah-ai-demo.onrender.com/drive/callback
http://localhost:8080/drive/callback
```

### 1.5 Download Credentials
1. After creating the OAuth client, download the JSON file
2. Rename it to `google_credentials.json`
3. Keep this file secure - it contains sensitive information

## Step 2: Environment Configuration

### 2.1 For Render Deployment
In your Render dashboard, add these environment variables:

```
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=https://diriyah-ai-demo.onrender.com/drive/callback
```

### 2.2 For Local Development
Update your `.env` file:

```
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8080/drive/callback
```

## Step 3: Service Account (Optional - For Server-to-Server)

If you want server-to-server access without user authentication:

### 3.1 Create Service Account
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Name it "Diriyah AI Service Account"
4. Grant it "Editor" role or custom Drive permissions

### 3.2 Generate Key
1. Click on the created service account
2. Go to "Keys" tab
3. Click "Add Key" > "Create New Key"
4. Choose JSON format
5. Download and save as `service_account.json`

### 3.3 Share Drive Folders
For the service account to access specific folders:
1. Get the service account email from the JSON file
2. Share your Google Drive folders with this email
3. Grant appropriate permissions (Viewer/Editor)

## Step 4: Testing the Integration

### 4.1 Test Authentication Flow
1. Deploy your application to Render
2. Visit `https://diriyah-ai-demo.onrender.com`
3. Try the Google Drive integration features
4. Check that authentication redirects work properly

### 4.2 Verify API Access
The system should be able to:
- List files from connected Google Drive
- Search for documents
- Download and process files
- Display file metadata

## Step 5: Security Considerations

### 5.1 Scopes
Only request necessary scopes:
- `https://www.googleapis.com/auth/drive.readonly` - Read-only access
- `https://www.googleapis.com/auth/drive.file` - Access to files created by the app

### 5.2 Credential Security
- Never commit credentials to version control
- Use environment variables for all sensitive data
- Regularly rotate API keys and secrets
- Monitor API usage in Google Cloud Console

### 5.3 User Consent
- Clearly explain what data you're accessing
- Provide privacy policy and terms of service
- Allow users to revoke access

## Step 6: Troubleshooting

### Common Issues

**"redirect_uri_mismatch" Error:**
- Verify the redirect URI exactly matches what's configured in Google Cloud Console
- Check for trailing slashes or HTTP vs HTTPS mismatches

**"invalid_client" Error:**
- Verify client ID and secret are correctly set in environment variables
- Check that the OAuth client is properly configured

**"access_denied" Error:**
- User declined authorization
- Check OAuth consent screen configuration
- Verify requested scopes are appropriate

**API Quota Exceeded:**
- Check usage in Google Cloud Console
- Request quota increase if needed
- Implement proper caching and rate limiting

### Debug Steps
1. Check Render logs for detailed error messages
2. Verify environment variables are set correctly
3. Test with a simple API call first
4. Use Google's OAuth 2.0 Playground for testing

## Step 7: Production Checklist

Before going live:
- [ ] OAuth consent screen is properly configured
- [ ] All redirect URIs are correct for production domain
- [ ] Environment variables are set in Render
- [ ] API quotas are sufficient for expected usage
- [ ] Error handling is implemented
- [ ] User privacy and data handling policies are in place
- [ ] Monitoring and logging are configured

## Support

For additional help:
- [Google Drive API Documentation](https://developers.google.com/drive/api)
- [OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)

Your domain configuration:
- **Production**: `https://diriyah-ai-demo.onrender.com`
- **Development**: `http://localhost:8080`

