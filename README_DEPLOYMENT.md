# QR Scanner - Vercel Deployment

## Environment Variables Required

Copy these environment variables to your Vercel project settings:

```bash
SECRET_KEY=your-secret-key-here
UPLOAD_FOLDER=/tmp/uploads
MAX_CONTENT_LENGTH=52428800
LOG_LEVEL=INFO
THREADS=4
TIMEOUT_DEFAULT=10
LANGEXTRACT_API_KEY=your-langextract-api-key
GOOGLE_API_KEY=your-google-api-key
```

## Deployment Steps

1. Connect your GitHub repository to Vercel
2. Configure environment variables in Vercel dashboard
3. Deploy using the provided `vercel.json` configuration

## Files Structure

- `app.py` - Main application entry point for Vercel
- `vercel.json` - Vercel deployment configuration
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version specification
- `.vercelignore` - Files to ignore during deployment

## Notes

- The application uses serverless functions on Vercel
- File uploads are stored in `/tmp` (temporary storage)
- WebSocket functionality may be limited on serverless platforms