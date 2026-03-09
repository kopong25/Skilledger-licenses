#!/bin/bash

# SkillLedger Frontend - Quick Deploy to Vercel

echo "=========================================="
echo "SkillLedger Frontend - Vercel Deployment"
echo "=========================================="
echo ""

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "📦 Installing Vercel CLI..."
    npm install -g vercel
fi

echo "✓ Vercel CLI ready"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API URL and API key"
    echo "   VITE_API_URL=https://your-backend.onrender.com"
    echo "   VITE_API_KEY=your_api_key"
    echo ""
    read -p "Press Enter when ready to continue..."
fi

echo "Installing dependencies..."
npm install

echo ""
echo "Testing build locally..."
npm run build

if [ $? -eq 0 ]; then
    echo "✓ Build successful"
else
    echo "❌ Build failed. Please fix errors and try again."
    exit 1
fi

echo ""
echo "=========================================="
echo "Ready to deploy to Vercel!"
echo "=========================================="
echo ""
echo "Run one of these commands:"
echo ""
echo "1. Deploy to production:"
echo "   vercel --prod"
echo ""
echo "2. Deploy to preview:"
echo "   vercel"
echo ""
echo "First time? The CLI will:"
echo "  1. Ask you to login"
echo "  2. Create a new project"
echo "  3. Deploy your app"
echo "  4. Give you a live URL!"
echo ""
echo "=========================================="
