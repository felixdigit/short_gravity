#!/bin/bash

# Script to add environment variables to Vercel
# This makes it easier to manage multiple variables across environments

echo "🔧 Vercel Environment Variable Setup"
echo "===================================="
echo ""
echo "This script will help you add environment variables to Vercel."
echo "You'll need to provide values for each variable."
echo ""

# Function to add an environment variable to Vercel
add_env_var() {
    local var_name=$1
    local var_description=$2
    local environments=$3  # "development,preview,production"

    echo ""
    echo "📝 Adding: $var_name"
    echo "   Description: $var_description"
    echo "   Environments: $environments"
    echo ""

    # Add to specified environments
    vercel env add "$var_name" "$environments"
}

echo "Choose what to set up:"
echo "1) X (Twitter) API variables"
echo "2) General configuration"
echo "3) All variables"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1|3)
        echo ""
        echo "=== X API Configuration ==="
        add_env_var "X_API_KEY" "X API Key from developer.x.com" "development,preview,production"
        add_env_var "X_API_SECRET" "X API Secret" "development,preview,production"
        add_env_var "X_BEARER_TOKEN" "X Bearer Token" "development,preview,production"
        add_env_var "X_CLIENT_ID" "X Client ID" "development,preview,production"
        add_env_var "X_CLIENT_SECRET" "X Client Secret" "development,preview,production"
        ;;
esac

case $choice in
    2|3)
        echo ""
        echo "=== General Configuration ==="
        add_env_var "NEXT_PUBLIC_API_BASE_URL" "API Base URL" "development,preview,production"
        add_env_var "NEXT_PUBLIC_ENABLE_DEBUG_MODE" "Enable debug mode (true/false)" "development,preview"
        ;;
esac

echo ""
echo "✅ Environment variables setup complete!"
echo ""
echo "To view your variables, run: vercel env ls"
echo "To pull them locally, run: vercel env pull .env.local"
