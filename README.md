# AI Datawrapper Agent API

An Azure Function that creates Datawrapper charts from Google Sheets via URL.

## 🚀 Features

- **File URL Support**: Accepts Google Sheets file URLs
- **Multiple Chart Types**: Supports various Datawrapper chart types (bars, lines, pie, maps, etc.)
- **Automatic Processing**: Downloads, parses, and converts data to CSV format
- **Rich Metadata**: Supports chart titles, descriptions, sources, and custom colors
- **Split Endpoints**: Two-step process for creating and updating charts
- **OpenAPI 3.1**: Complete API specification included
- **Comprehensive Testing**: Local and Azure deployment testing scripts

## 📋 Prerequisites

- Python 3.12+
- Azure Functions Core Tools
- Datawrapper API token
- Azure subscription (for deployment)

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client App    │───▶│  Azure Function  │───▶│  Datawrapper    │
│                 │    │                  │    │     API         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │ Google Sheets    │
                       └──────────────────┘
```

## 🔧 Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd ai-datawrapper-agent-api
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   # Update local.settings.json with your Datawrapper token
   cp local.settings.json.example local.settings.json
   # Edit local.settings.json and add your DATAWRAPPER_TOKEN
   ```

4. **Run locally**
   ```bash
   func start
   ```

### Azure Deployment

1. **Quick deployment**
   ```bash
   ./quick_deploy.sh
   ```

2. **Full deployment with environment variables**
   ```bash
   ./deploy_new_function.sh
   ```

## 📖 API Usage

### Single Endpoint Approach

**POST** `/api/create_chart`

Creates a Datawrapper chart from a file URL in one step.

**Authentication**: Uses Azure Function key authentication. Include the function key in the URL or as a query parameter.

#### Request Body

```json
{
  "file_url": "https://docs.google.com/spreadsheets/d/1b_h7Wkd1y1-sNjkeR4izCowbRqLpeIS0FYmZkI/edit?usp=sharing",
  "chart_type": "d3-bars-stacked",
  "title": "Sales Data by Region",
  "intro": "This chart shows quarterly sales performance across different regions.",
  "byline": "Data source: Company Sales Database",
  "source_name": "Company Sales Database",
  "source_url": "https://example.com/sales-data",
  "custom_colors": ["#ff6b6b", "#4ecdc4", "#45b7d1"]
}
```

### Split Endpoints Approach

#### Step 1: Create Chart ID and Upload Data

**POST** `/api/create_chart_id`

Creates a new chart and uploads data from the file URL.

```json
{
  "file_url": "https://docs.google.com/spreadsheets/d/1b_h7Wkd1y1-sNjkeR4izCowbRqLpeIS0FYmZkIFSInk/edit?usp=sharing",
  "chart_type": "d3-bars",
  "title": "Sales Data by Region"
}
```

**Response:**
```json
{
  "status": "success",
  "chart_id": "abc123def456",
  "message": "Chart created and data uploaded successfully"
}
```

#### Step 2: Update Chart Metadata and Publish

**POST** `/api/update_chart`

Updates chart metadata and publishes the chart.

```json
{
  "chart_id": "abc123def456",
  "intro": "This chart shows quarterly sales performance across different regions.",
  "byline": "Data source: Company Sales Database",
  "source_name": "Company Sales Database",
  "source_url": "https://example.com/sales-data",
  "custom_colors": ["#ff6b6b", "#4ecdc4", "#45b7d1"]
}
```

**Response:**
```json
{
  "status": "success",
  "chart_id": "abc123def456",
  "chart_url": "https://www.datawrapper.de/_/abc123def456/",
  "message": "Chart metadata updated and published successfully"
}
```

### Supported File Types

- **Google Sheets**: `https://docs.google.com/spreadsheets/d/{sheet_id}/edit`

### Supported Chart Types

- `d3-bars-stacked` - Stacked bar chart
- `d3-bars` - Bar chart
- `d3-lines` - Line chart
- `d3-pie` - Pie chart
- `d3-scatter` - Scatter plot
- `d3-maps-choropleth` - Choropleth map
- `d3-maps-symbols` - Symbol map
- `d3-bars-horizontal` - Horizontal bar chart
- `d3-bars-grouped` - Grouped bar chart
- `d3-lines-multi` - Multi-line chart

## 🧪 Testing

### Split Endpoints Test
```bash
./test_split_curl.sh
```

## 📚 Documentation

- [OpenAPI Specification](openapi.yaml) - Complete API documentation
- [Deployment Guide](Deploy/DEPLOYMENT.md) - Local and Azure deployment instructions

## 🔐 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATAWRAPPER_TOKEN` | Datawrapper API authentication token | Yes |

## 🏗️ Project Structure

```
ai-datawrapper-agent-api/
├── Agent/
│   ├── Agent-README.md     # Agent documentation
│   └── system_prompt.txt   # System prompt for AI agent
├── Deploy/
│   ├── deploy_new_function.sh # Full deployment with environment setup
│   ├── quick_deploy.sh        # Quick Azure deployment script
│   └── DEPLOYMENT.md          # Deployment instructions
├── endpoints/
│   ├── __init__.py
│   ├── datawrapper.py      # Main chart creation logic
│   ├── models.py           # Pydantic models
│   └── root.py             # Health check endpoint
├── function_app.py         # Azure Function entry point
├── host.json               # Azure Functions configuration
├── local.settings.json     # Local development settings
├── local.settings.json.example # Example settings file
├── requirements.txt        # Python dependencies
├── openapi.yaml           # API specification
├── test_split_curl.sh     # Split endpoints testing
└── README.md              # This file
```

## 🚀 Deployment

### Quick Deployment
```bash
cd Deploy
./quick_deploy.sh
```

### Full Deployment with Environment Setup
```bash
cd Deploy
./deploy_new_function.sh
```

### Manual Azure Functions Deployment

1. **Create Function App**
   ```bash
   az functionapp create \
     --name ai-datawrapper-agent-api \
     --resource-group your-resource-group \
     --consumption-plan-location eastus \
     --runtime python \
     --runtime-version 3.12 \
     --functions-version 4
   ```

2. **Set environment variables**
   ```bash
   az functionapp config appsettings set \
     --name ai-datawrapper-agent-api \
     --resource-group your-resource-group \
     --settings DATAWRAPPER_TOKEN="your-token"
   ```

3. **Deploy**
   ```bash
   func azure functionapp publish ai-datawrapper-agent-api
   ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Review the [OpenAPI Specification](openapi.yaml) for API details
- Check the [Deployment Guide](Deploy/DEPLOYMENT.md) for troubleshooting
- Open an issue on GitHub

## 🔗 Links

- [Datawrapper API Documentation](https://developer.datawrapper.de/)
- [Azure Functions Documentation](https://docs.microsoft.com/en-us/azure/azure-functions/)
- [OpenAPI Specification](https://swagger.io/specification/) 