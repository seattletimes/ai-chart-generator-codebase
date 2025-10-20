# Deployment Guide: Local Testing & Azure Deployment

This guide walks you through testing your Azure Function locally and then deploying it to Azure.

## 📁 **Project Structure**
- **Deploy scripts**: Located in `Deploy/` folder
  - `quick_deploy.sh` - Quick deployment script
  - `deploy_new_function.sh` - Full deployment with environment setup
- **Test scripts**: Located in project root
  - `test_split_curl.sh` - Test the deployed function
- **Configuration**: Located in project root
  - `local.settings.json` - Local development settings
  - `requirements.txt` - Python dependencies

## 🏠 **Part 1: Local Testing**

### Prerequisites
- Azure Functions Core Tools (✅ Already installed)
- Python 3.12+ 
- Datawrapper API token

### Step 1: Install Dependencies
```bash
# From the project root directory
pip install -r requirements.txt
```

### Step 2: Configure Local Settings
1. **Update `local.settings.json`**:
   - Replace `YOUR_DATAWRAPPER_TOKEN_HERE` with your actual Datawrapper API token
   - Get your token from: https://app.datawrapper.de/account/api-tokens
   - Add `API_KEY` with a secure API key for endpoint authentication

### Step 3: Prepare Test URLs
1. Update the test URLs in `test_split_curl.sh` to point to your Google Sheets files
2. Ensure your files are publicly accessible or properly shared

### Step 4: Start Local Function
```bash
func start
```
This will start the function on `http://localhost:7071`

### Step 5: Test Locally
In a new terminal:
```bash
# Test using the curl script
./test_split_curl.sh
```

### Step 6: Test Split Endpoints (Optional)
```bash
# From the project root directory
./test_split_curl.sh
```

## ☁️ **Part 2: Azure Deployment**

### Prerequisites
- Azure CLI installed and logged in
- Azure subscription with billing enabled
- Resource group (or create one)

### Option 1: Quick Deployment
```bash
# From the Deploy directory
cd Deploy
./quick_deploy.sh
```

### Option 2: Full Deployment with Environment Setup
```bash
# From the Deploy directory
cd Deploy
./deploy_new_function.sh
```

### Option 3: Manual Deployment

#### Step 1: Login to Azure
```bash
az login
```

#### Step 2: Set Variables
```bash
# Set your variables (update these values)
RESOURCE_GROUP="your-resource-group-name"
STORAGE_ACCOUNT="aidatawrapperstorage$(date +%s)"
LOCATION="eastus"  # or your preferred region
FUNCTION_APP="ai-datawrapper-agent-api"
```

#### Step 3: Create Resource Group (if needed)
```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

#### Step 4: Create Storage Account
```bash
az storage account create \
  --name $STORAGE_ACCOUNT \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --sku Standard_LRS
```

#### Step 5: Create Function App
```bash
az functionapp create \
  --resource-group $RESOURCE_GROUP \
  --consumption-plan-location $LOCATION \
  --runtime python \
  --runtime-version 3.12 \
  --functions-version 4 \
  --name $FUNCTION_APP \
  --storage-account $STORAGE_ACCOUNT \
  --os-type linux
```

#### Step 6: Configure Environment Variables
```bash
# Set Datawrapper API token
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings DATAWRAPPER_TOKEN="your-actual-datawrapper-token"

# Set API key for endpoint authentication
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings API_KEY="your-secure-api-key-here"
```

#### Step 7: Deploy Function
```bash
# Deploy from project root directory
cd ..  # Go back to project root from Deploy directory
func azure functionapp publish $FUNCTION_APP
```

#### Step 8: Get Function URL
```bash
# Get the function URL
az functionapp function show \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --function-name create_chart
```

## 🧪 **Part 3: Testing Deployed Function**

### Step 1: Update Test Scripts
Update the URL in your test scripts:
```python
AZURE_FUNCTION_URL = "https://<your-azure-function-api>.azurewebsites.net/api"
```

### Step 2: Test Deployed Function
```bash
# Test using the curl script (from project root)
./test_split_curl.sh
```

## 🔧 **Troubleshooting**

### Local Issues
1. **Port already in use**: Change port in `local.settings.json`
2. **Missing dependencies**: Run `pip install -r requirements.txt`
3. **Token issues**: Verify `DATAWRAPPER_TOKEN` in `local.settings.json`
4. **API key issues**: Verify `API_KEY` in `local.settings.json`

### Azure Issues
1. **Deployment fails**: Check Azure CLI login and permissions
2. **Function not found**: Verify function name in `function_app.py`
3. **Environment variables**: Check in Azure Portal → Configuration

### Common Commands
```bash
# Check function status
az functionapp show --name $FUNCTION_APP --resource-group $RESOURCE_GROUP

# View logs
az functionapp logs tail --name $FUNCTION_APP --resource-group $RESOURCE_GROUP

# Delete function app (if needed)
az functionapp delete --name $FUNCTION_APP --resource-group $RESOURCE_GROUP
```

## 📊 **Monitoring**

### Azure Portal
- Go to your Function App
- Check "Monitor" for logs and metrics
- Use "Test/Run" to test directly in portal

### Logs
- Application logs: Azure Portal → Function App → Monitor
- Function-specific logs: Function → Monitor → Logs

## 🔐 **Security Notes**

1. **API Token**: Store securely in Azure Key Vault for production
2. **CORS**: Configure CORS settings if calling from web browsers
3. **Authentication**: Consider adding Azure AD authentication for production

## 📈 **Scaling**

### Consumption Plan (Current)
- Pay per execution
- Auto-scales to zero
- Good for development/testing

### Premium Plan (Production)
- Always warm
- Better performance
- VNet integration
- More features

To upgrade:
```bash
az functionapp plan create \
  --name "premium-plan" \
  --resource-group $RESOURCE_GROUP \
  --sku EP1 \
  --is-linux

az functionapp update \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --plan "premium-plan"
```

## 🚀 **Available Endpoints**

### Single Endpoint
- **POST** `/api/create_chart` - Creates chart in one step

### Split Endpoints
- **POST** `/api/create_chart_id` - Step 1: Create chart and upload data
- **POST** `/api/update_chart` - Step 2: Update metadata and publish

### Utility Endpoints
- **GET** `/api/` - Health check and API information 