#!/bin/bash

# New Azure Function Deployment Script
# Usage: ./deploy_new_function.sh

set -e  # Exit on any error

echo "🚀 Starting New Azure Function Deployment..."

# Configuration - UPDATE THESE VALUES
RESOURCE_GROUP="rg-your-resource-group"
LOCATION="eastus"
FUNCTION_APP="ai-datawrapper-agent-api"

# Try to read environment variables from local.settings.json if it exists
if [ -f "local.settings.json" ]; then
    echo "📄 Reading environment variables from local.settings.json..."
    DATAWRAPPER_TOKEN=$(python3 -c "import json; print(json.load(open('local.settings.json'))['Values']['DATAWRAPPER_TOKEN'])" 2>/dev/null || echo "YOUR_DATAWRAPPER_TOKEN_HERE")
    X_API_KEY=$(python3 -c "import json; print(json.load(open('local.settings.json'))['Values']['X_API_KEY'])" 2>/dev/null || echo "your-secure-api-key-here")
else
    DATAWRAPPER_TOKEN="YOUR_DATAWRAPPER_TOKEN_HERE"  # Update this!
    X_API_KEY="your-secure-api-key-here"  # Update this!
fi

# Fixed storage account name (no date suffix)
STORAGE_ACCOUNT="aidatawrapperstoragedev"

echo "📋 Configuration:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo "  Function App: $FUNCTION_APP"
echo "  Storage Account: $STORAGE_ACCOUNT"
echo "  Datawrapper Token: ${DATAWRAPPER_TOKEN:0:10}..."  # Show first 10 chars for security
echo "  API Key: ${X_API_KEY:0:10}..."  # Show first 10 chars for security
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    echo "   Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "🔐 Please log in to Azure..."
    az login
fi

echo "✅ Azure CLI ready"

# Validate environment variables
echo "🔍 Validating environment variables..."
if [ "$DATAWRAPPER_TOKEN" = "YOUR_DATAWRAPPER_TOKEN_HERE" ] || [ "$DATAWRAPPER_TOKEN" = "" ]; then
    echo "❌ ERROR: DATAWRAPPER_TOKEN is not set. Please update it in the script or local.settings.json"
    exit 1
fi

if [ "$X_API_KEY" = "your-secure-api-key-here" ] || [ "$X_API_KEY" = "" ]; then
    echo "❌ ERROR: X_API_KEY is not set. Please update it in the script or local.settings.json"
    exit 1
fi

echo "✅ Environment variables validated"

# Check if resource group exists
if az group show --name $RESOURCE_GROUP &> /dev/null; then
    echo "📦 Resource group '$RESOURCE_GROUP' already exists - reusing"
else
    echo "📦 Creating resource group..."
    az group create --name $RESOURCE_GROUP --location $LOCATION --output none
    echo "✅ Resource group created"
fi

# Check if storage account exists
if az storage account show --name $STORAGE_ACCOUNT --resource-group $RESOURCE_GROUP &> /dev/null; then
    echo "💾 Storage account '$STORAGE_ACCOUNT' already exists - reusing"
else
    echo "💾 Creating storage account..."
    az storage account create \
      --name $STORAGE_ACCOUNT \
      --location $LOCATION \
      --resource-group $RESOURCE_GROUP \
      --sku Standard_LRS \
      --output none
    echo "✅ Storage account created"
fi

# Check if function app exists
if az functionapp show --name $FUNCTION_APP --resource-group $RESOURCE_GROUP &> /dev/null; then
    echo "⚡ Function app '$FUNCTION_APP' already exists - updating"
else
    echo "⚡ Creating function app..."
    az functionapp create \
      --resource-group $RESOURCE_GROUP \
      --consumption-plan-location $LOCATION \
      --runtime python \
      --runtime-version 3.12 \
      --functions-version 4 \
      --name $FUNCTION_APP \
      --storage-account $STORAGE_ACCOUNT \
      --os-type linux \
      --disable-app-insights \
      --output none
    echo "✅ Function app created"
fi

# Configure environment variables (this will update existing settings)
echo "🔧 Configuring environment variables..."
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings DATAWRAPPER_TOKEN="$DATAWRAPPER_TOKEN" X_API_KEY="$X_API_KEY" \
  --output none
echo "✅ Environment variables configured"

# Wait for function app to be ready before deployment
echo "⏳ Waiting for function app to be ready..."
sleep 30

# Deploy function with retry logic
echo "🚀 Deploying function..."
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    echo "Attempt $((RETRY_COUNT + 1)) of $MAX_RETRIES..."
    
    if func azure functionapp publish $FUNCTION_APP --python; then
        echo "✅ Function deployed successfully"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "⚠️  Deployment failed. Retrying in 30 seconds..."
            sleep 30
        else
            echo "❌ Function deployment failed after $MAX_RETRIES attempts"
            echo "💡 Troubleshooting tips:"
            echo "   1. Check if the function app is fully initialized"
            echo "   2. Verify environment variables are set correctly"
            echo "   3. Try running: az functionapp restart --name $FUNCTION_APP --resource-group $RESOURCE_GROUP"
            echo "   4. Check logs: az functionapp logs tail --name $FUNCTION_APP --resource-group $RESOURCE_GROUP"
            exit 1
        fi
    fi
done

# Get function URL
echo "🔗 Getting function URL..."
FUNCTION_URL=$(az functionapp function show \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --function-name create_chart_endpoint \
  --query "invokeUrlTemplate" \
  --output tsv 2>/dev/null || echo "Function URL not available yet")

echo ""
echo "🎉 Deployment Complete!"
echo "========================"
echo "Function App: $FUNCTION_APP"
echo "Resource Group: $RESOURCE_GROUP"
echo "Function URL: $FUNCTION_URL"
echo ""
echo "🔧 Environment Variables Configured:"
echo "  - DATAWRAPPER_TOKEN: ${DATAWRAPPER_TOKEN:0:10}..."
echo "  - X_API_KEY: ${X_API_KEY:0:10}..."
echo ""
echo "📝 Next Steps:"
echo "1. Update your test scripts with the function URL above"
echo "2. Test the function: python quick_test.py"
echo "3. Monitor logs: az functionapp logs tail --name $FUNCTION_APP --resource-group $RESOURCE_GROUP"
echo ""
echo "🔗 Azure Portal: https://portal.azure.com/#@/resource/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Web/sites/$FUNCTION_APP" 