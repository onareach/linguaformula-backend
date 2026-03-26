#!/bin/bash
# Deployment script for LinguaFormula backend to Heroku

set -e  # Exit on error

echo "🚀 Deploying LinguaFormula backend to Heroku..."

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI is not installed. Please install it first:"
    echo "   brew install heroku/brew/heroku"
    exit 1
fi

# Check if logged in to Heroku
if ! heroku auth:whoami &> /dev/null; then
    echo "⚠️  Not logged in to Heroku. Please run: heroku login"
    exit 1
fi

# Get app name from argument or use default
APP_NAME=${1:-linguaformula-backend}

echo "📦 App name: $APP_NAME"

# Check if app exists
if heroku apps:info $APP_NAME &> /dev/null; then
    echo "✅ Heroku app '$APP_NAME' already exists"
else
    echo "📝 Creating new Heroku app: $APP_NAME"
    heroku create $APP_NAME
fi

# Add PostgreSQL addon if not already added
if heroku addons:info heroku-postgresql -a $APP_NAME &> /dev/null; then
    echo "✅ PostgreSQL addon already exists"
else
    echo "📦 Adding PostgreSQL addon..."
    echo "   Using heroku-postgresql:essential-0 (free tier, ~$5/month)"
    # Use essential-0 (the current free/low-cost tier, replaces the old "mini" plan)
    if heroku addons:create heroku-postgresql:essential-0 -a $APP_NAME; then
        echo "✅ Created heroku-postgresql:essential-0"
        echo "   ⏳ Database is being created in the background..."
        echo "   💡 The app will restart automatically when the database is ready"
    else
        echo "❌ Failed to create PostgreSQL addon"
        echo ""
        echo "💡 Please create the addon manually:"
        echo "   heroku addons:create heroku-postgresql:essential-0 -a $APP_NAME"
        echo ""
        echo "   Or check available plans:"
        echo "   heroku addons:plans heroku-postgresql"
        exit 1
    fi
fi

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY environment variable is not set."
    echo "   Please set it with: heroku config:set OPENAI_API_KEY=your_key_here -a $APP_NAME"
else
    echo "🔑 Setting OPENAI_API_KEY..."
    heroku config:set OPENAI_API_KEY=$OPENAI_API_KEY -a $APP_NAME
fi

# Add Heroku remote if not exists
if git remote | grep -q "^heroku$"; then
    echo "✅ Heroku remote already configured"
else
    echo "🔗 Adding Heroku remote..."
    heroku git:remote -a $APP_NAME
fi

# Deploy
echo "📤 Deploying to Heroku..."
git push heroku main

echo ""
echo "✅ Deployment complete!"
echo "🌐 Your app should be available at: https://$APP_NAME.herokuapp.com"
echo ""
echo "📋 Next steps:"
echo "   1. Set OPENAI_API_KEY if not already set:"
echo "      heroku config:set OPENAI_API_KEY=your_key_here -a $APP_NAME"
echo "   2. Run database migrations:"
echo "      heroku run 'psql \$DATABASE_URL -f migrations/initial_schema.sql' -a $APP_NAME"
echo "      heroku run 'psql \$DATABASE_URL -f migrations/schema_migration.sql' -a $APP_NAME"
echo "   3. Check app logs:"
echo "      heroku logs --tail -a $APP_NAME"
