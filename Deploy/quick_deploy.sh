#!/bin/bash

# Quick Azure Function Update Script
# Fast deployment without environment variable sync
# Usage: ./quick_update.sh

echo "⚡ Quick Azure Function Update..."

# Configuration
RESOURCE_GROUP="rg-seattle-times-beta"

#Prod Function App
#FUNCTION_APP="ai-datawrapper-agent-api"

#dev Function App
FUNCTION_APP="ai-datawrapper-agent-api-dev"


echo "📋 Deploying to: $FUNCTION_APP"

# Quick deployment
echo "🚀 Deploying function code..."
func azure functionapp publish $FUNCTION_APP --python --resource-group $RESOURCE_GROUP

echo ""
echo "✅ Quick update complete!"
echo "Function App: $FUNCTION_APP"
echo ""
echo "💡 For full update with environment variables, use: ./update_azure.sh" 