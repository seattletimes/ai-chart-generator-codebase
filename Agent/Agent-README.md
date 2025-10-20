# Chart Generator Agent (Custom GPT) Setup Guide

This guide provides step-by-step instructions for creating the **Chart Generator Agent** as a custom GPT in ChatGPT Enterprise. This AI agent gives Seattle Times newsroom staff a conversational way to turn a public Google Sheet into a published **Datawrapper** chart, with rapid, iterative refinements.

---

## Overview

The Chart Generator Agent:
- **Creates** a Datawrapper chart from a publicly shared Google Sheets URL
- **Collects** required chart metadata (type, title, source name) and optional enhancements (intro, byline, source URL, custom colors)
- **Publishes** the chart and returns a live Datawrapper URL
- **Iterates** on chart settings (same `chart_id`) until the user finalizes
- **Enforces** input validation and clear error handling based on the backing API

### Two‑Step Flow (Actions)
1. **Create Chart ID** (`POST /create_chart_id`) – create the chart and upload data from the provided file URL.
2. **Update & Publish** (`POST /update_chart`) – update chart metadata (intro/byline/source/custom colors) and publish; returns the live chart URL.

> The agent maintains a single **current chart session** (one `chart_id`) for iterative tweaks until the user says **Finalize**.

---

## Prerequisites

### Required Access
- **ChatGPT Enterprise** account with MyGPT creation permissions
- **Admin access** to deploy and manage the Azure Functions/API (see project README)
- **Datawrapper API token** stored in the backend API configuration
- **Azure Functions host key** (Functions key) to call the API (sent via header `x-functions-key`)

### Required Files
Ensure you have access to the following files in the repository:
- `Agents/system_prompt.txt` – Core agent instructions and behavior
- `openapi.yaml` – OpenAPI 3.1 schema for the Azure Function API

> Reference: The `system_prompt.txt` file is in the `Agents/` folder; `openapi.yaml` is at the project root.

---

## Step‑by‑Step Setup Instructions

### Step 1: Deploy the Supporting API

1. **Navigate to the project directory** (see main project README for details).
2. **Deploy the Azure Functions app** (or Azure Web App for Functions) using your standard pipeline.
3. **Configure application settings**:
   - `DATAWRAPPER_TOKEN` – your Datawrapper API token
   - Any other environment variables required by the API
4. **Note the Production endpoint** (e.g., `https://<your-azure-function-api>.azurewebsites.net/api`). You’ll use this in the custom GPT action schema.

### Step 2: Access ChatGPT Enterprise

1. Log into **ChatGPT Enterprise**.
2. Go to **MyGPTs** → **Create a GPT**.
3. Switch to the **Configure** tab for manual setup.

### Step 3: Configure Basic Information

**Name**
- `Chart Generator Agent`

**Description**
- `Conversational assistant for Seattle Times newsroom to create and iterate on Datawrapper charts from Google Sheets links.`

**Instructions**
- Copy/paste the **entire** content of `Agents/system_prompt.txt` into the **Instructions** field.
- This includes: role, step-by-step workflow, validation rules, and finalize behavior.

### Step 4: Configure Actions (API Integration)

1. Click **Create new action**.
2. **Import OpenAPI schema**:
   - Paste the full content of `openapi.yaml` into the schema field.
3. **Set Authentication**:
   - **Type**: API Key
   - **Custom Header Name**: `x-functions-key`
   - **API Key Value**: \<your Azure Functions host key>
4. **Verify Servers**:
   - Ensure the `servers` entry points to your deployed API, e.g.
     ```yaml
     servers:
       - url: https://<your-azure-function-api>.azurewebsites.net/api
         description: Production server
     ```
5. **Endpoints exposed by the schema**:
   - `POST /create_chart_id` – `operationId: createChartId`
   - `POST /update_chart` – `operationId: updateChart`

> The agent will call **/create_chart_id** once per session to obtain `chart_id`, then call **/update_chart** repeatedly for tweaks/publishing.

### Step 5: Configure Conversation Starters

Add these to help users begin:
1. **“Create a bar chart from this Google Sheet: <paste public link> — title it ‘Unemployment rate’ and set source to BLS.”**
2. **"Use this Google Sheets link to make a line chart titled 'Median home prices' — source: Zillow."**
3. **“Make a grouped bar chart from this sheet. Then change colors to {"Seattle":"#005c7a","Bellevue":"#8ecae6"}.”**
4. **“Convert this data into a choropleth map — title ‘Voter turnout by county’, source: SOS, link to source page.”**

### Step 6: Set Capabilities

- ✅ **Actions** (required; provided by OpenAPI schema)
- ✅ **Code Interpreter** (optional; helpful for light validation/text manipulation if needed)
- ❌ **Image Generation** (not required)
- 🌐 **Web Browsing** (optional; not required for core flow)

### Step 7: Privacy and Sharing

- Start with **Only me** for testing
- After validation, share with the **Newsroom** or relevant groups
- Ensure no private data is sent; require **publicly shared** file URLs

### Step 8: Test the Custom GPT

#### Quick Test Scripts (optional)
Use `curl` to sanity‑check the API (replace values as needed):

**Create Chart ID**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: $FUNCTIONS_KEY" \
  -d '{
    "file_url": "https://docs.google.com/spreadsheets/d/xxx/edit?usp=sharing",
    "chart_type": "d3-bars",
    "title": "Sample Chart"
  }' \
  https://<your-azure-function-api>.azurewebsites.net/api/create_chart_id
```

**Update & Publish**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: $FUNCTIONS_KEY" \
  -d '{
    "chart_id": "abc123def456",
    "source_name": "BLS",
    "intro": "Quarterly rates by metro.",
    "byline": "The Seattle Times",
    "source_url": "https://www.bls.gov/",
    "custom_colors": {"Seattle":"#005c7a","Bellevue":"#8ecae6"}
  }' \
  https://<your-azure-function-api>.azurewebsites.net/api/update_chart
```

#### In‑GPT Test Scenarios
1. **Happy Path** – Provide a valid Google Sheet URL, `chart_type`, `title`, and `source_name`; expect a **Datawrapper URL** back.
2. **URL Validation** – Give a non‑Google URL; expect the agent to prompt for a **public Google Sheets** link.
3. **Iterative Tweaks** – Change only colors or title; agent should **reuse the same `chart_id`**.
4. **Finalize** – Say “Finalize”; agent confirms and **won’t reuse** that `chart_id` next time.

#### Expected Behaviors (from system prompt)
- Maintains **one active `chart_id`** per session
- Validates URL patterns and optional fields (JSON for `custom_colors`)
- Never fabricates `chart_id` or `chart_url`
- Clear error messaging and retry guidance

---

## Troubleshooting

### Common API Responses
- **401 Unauthorized** – Invalid Functions key. Re‑enter `x-functions-key` in the action auth.
- **400 Bad Request** – Missing or invalid inputs (e.g., URL not Google Sheets, `custom_colors` not valid JSON).
- **500 Server Error** – Datawrapper token missing/misconfigured, chart not found, or file processing error.

### Agent‑Side Validation Messages
- Non‑supported link:
  > "Only publicly shared Google Sheets URLs are supported. Please make sure your link is public and copy the full sharing URL."
- Invalid `custom_colors`:
  > “Please provide custom_colors as a valid JSON string or an object like {"A": "#123456"}.”

### Debug Tips
- Confirm the Google Sheet is **publicly accessible**
- Verify `DATAWRAPPER_TOKEN` is set in the API environment
- Check server URL in the imported OpenAPI schema matches deployment
- Review Functions logs for detailed error traces

---

## Best Practices

### For Newsroom Users
1. **Share Data Publicly** – Use a public sharing link for Google Sheets
2. **Pick the Right Chart Type** – Choose from the allowed `d3-*` types listed by the agent
3. **Iterate Quickly** – Tweak only the fields you want to change; the agent keeps the rest
4. **Source Transparently** – Always set `source_name` (and `source_url` if applicable)

### For Administrators
1. **Lock Down Secrets** – Keep `x-functions-key` and `DATAWRAPPER_TOKEN` secure
2. **Monitor Errors** – Track 400/401/500 rates post‑release
3. **Version the Schema** – Update `openapi.yaml` and re‑import when endpoints evolve
4. **Document Chart Types** – Maintain a newsroom‑friendly cheatsheet of allowed chart types

---

## File Reference Guide

### Core Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| `system_prompt.txt` | `Agents/system_prompt.txt` | Core agent instructions and behavior |
| `openapi.yaml` | `/openapi.yaml` | API specification for chart creation & publishing |

### Supporting Infrastructure

| Component | Location | Purpose |
|-----------|----------|---------|
| Azure Functions / API | `api/` | Endpoints: `/create_chart_id`, `/update_chart` |
| Deployment Scripts | `deploy/` | Azure deployment automation |
| Documentation | `README.md` | Main project documentation |

---

## Maintenance & Updates

### Regular Tasks
- **Monthly** – Review API error logs; validate Datawrapper token; test with a real sheet
- **Quarterly** – Revisit chart type defaults, newsroom color palettes, and copy guidance
- **As Needed** – Update `openapi.yaml` and re‑import Actions when endpoint contracts change

### Success Metrics
- **Time to First Chart (TTFC)** – From link paste to published URL
- **Iteration Velocity** – Average tweaks per chart session
- **Error Rate** – 4xx/5xx per 100 requests
- **Adoption** – Active newsroom users per week

---

## Quick Reference

**Allowed `chart_type` values**
- `d3-bars-stacked`, `d3-bars`, `d3-bars-horizontal`, `d3-bars-grouped`
- `d3-lines`, `d3-lines-multi`
- `d3-pie`, `d3-scatter`
- `d3-maps-choropleth`, `d3-maps-symbols`

**Key Endpoints**
- `POST /create_chart_id` → returns `{ status, chart_id }`
- `POST /update_chart` → returns `{ status, chart_id, chart_url }`

**Auth Header**
- `x-functions-key: <Functions host key>`

**Datawrapper URL Format**
- `https://www.datawrapper.de/_/<chart_id>/`

---

**Support**
- For deployment issues: see `deploy/` and main `README.md`
- For agent behavior: review `Agents/system_prompt.txt`
- For API contract: `openapi.yaml`

