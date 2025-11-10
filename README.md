# 🤖 Multitenant Bot with Azure OpenAI

Intelligent bot built with **Microsoft Agents SDK** integrating **Azure OpenAI** with full support for **multitenant** scenarios using **User-Assigned Managed Identity**.

## 🎯 Key Features

- ✅ **User-Assigned Managed Identity authentication** (Microsoft recommended)
- ✅ **Multitenant support** with optional tenant validation
- ✅ **Response streaming** for better user experience
- ✅ **Direct Azure OpenAI integration** for intelligent responses
- ✅ **Production-ready** for Azure Web App deployment
- ✅ **Robust logging** and error handling
- ✅ **Complies with Microsoft guidelines** (post-July 2025)
- ✅ **Secure networking** with VNet integration support
- ✅ **Application Insights** for monitoring

## 📅 Important: July 2025 Changes

Microsoft **deprecated MultiTenant bot creation** after July 31, 2025. This project uses **User-Assigned Managed Identity**, which is Microsoft's **recommended** approach for new developments.

**What does this mean?**
- ✅ Existing MultiTenant bots **will continue to work**
- ❌ **Cannot** create new MultiTenant bots
- ✅ **User-Assigned Managed Identity** is the recommended option
- ✅ This project is already configured correctly

## 🏗️ Architecture

```
User (Teams/Web Chat)
    ↓
Azure Bot Service (with Managed Identity)
    ↓
Azure App Service (your Python code) ← VNet Integration
    ↓                                   ↓
Azure OpenAI (streaming)          Application Insights
    ↓
AI Foundry (model deployment)
```

---

# 📘 Complete Setup Guide: Step-by-Step

This guide walks you through creating the entire solution from scratch, including all required Azure resources, networking, security, and Teams manifest deployment.

**📖 For detailed step-by-step instructions**, see the [SETUP_GUIDE.md](SETUP_GUIDE.md) file.

## Quick Links

- [Azure Resources Overview](SETUP_GUIDE.md#1-azure-resources-overview)
- [Prerequisites](SETUP_GUIDE.md#2-prerequisites)
- [Networking Infrastructure](SETUP_GUIDE.md#4-step-2-create-networking-infrastructure)
- [AI Foundry and Azure OpenAI Setup](SETUP_GUIDE.md#7-step-5-deploy-ai-foundry-and-azure-openai)
- [Teams Manifest Creation](SETUP_GUIDE.md#11-step-9-create-and-deploy-teams-manifest)
- [Troubleshooting Guide](SETUP_GUIDE.md#-troubleshooting)

---

**Key Components:**
- `src/agent.py` - Bot logic with multitenant validation
- `src/start_server.py` - Aiohttp HTTP server
- `src/main.py` - Application entry point

## 📋 Prerequisites

### Azure Resources (must have already)
- ✅ Azure Bot Service
- ✅ User-Assigned Managed Identity
- ✅ Azure Web App
- ✅ Azure OpenAI Service

### Development Tools
- Python 3.10+
- Azure CLI
- Git (optional, for deployment)

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone <your-repo>
cd BotPlusAzureOpenAI
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Bot Framework Authentication (User-Assigned Managed Identity)
MicrosoftAppType=UserAssignedMSI
MicrosoftAppId=<your-managed-identity-client-id>
MicrosoftAppPassword=
MicrosoftAppTenantId=<your-tenant-id>

# Multitenant Access Control (Optional)
# Leave empty to allow ALL tenants (public bot)
# Or comma-separated list: tenant-id-1,tenant-id-2
ALLOWED_TENANTS=

# Azure OpenAI Configuration
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_DEPLOYMENT_NAME=<your-deployment-name>
```

### 4. Run locally

```bash
python src/start_server.py
```

The bot will be available at: `http://localhost:3978`

## 🔐 Multitenant Validation

### What is it?

The bot can **restrict access** to specific Azure AD organizations (tenants).

### Configuration

#### Public Bot (allows all tenants)
```env
ALLOWED_TENANTS=
```

#### Private Bot (specific clients only)
```env
ALLOWED_TENANTS=tenant-id-1,tenant-id-2,tenant-id-3
```

### How it works

The bot validates the user's `tenant_id` against the `ALLOWED_TENANTS` list. If not in the list, access is denied with a clear message.

**Code implementation** (in `src/agent.py`):
```python
# Get allowed tenants from environment
allowed_tenants_str = environ.get("ALLOWED_TENANTS", "").strip()

if allowed_tenants_str:
    allowed_tenants = [t.strip() for t in allowed_tenants_str.split(",")]
    user_tenant_id = getattr(context.activity.conversation, "tenant_id", None)
    
    if user_tenant_id and user_tenant_id not in allowed_tenants:
        # Deny access
        await context.send_activity("Unauthorized access")
        return
```

## 🚀 Deploy to Azure

### Deployment Options

You have **3 options** to deploy:

1. **GitHub Actions** (Recommended) - Automated CI/CD ⭐
2. **Azure CLI** - Manual deployment
3. **Git Deploy** - Push-based deployment

---

### Option 1: GitHub Actions (Recommended) ⭐

**Automated deployment on every push to main branch.**

#### Quick Setup:

1. **Get Azure Publish Profile:**
   - Go to Azure Portal → Your Web App
   - Click **Get publish profile** (download file)
   - Copy the entire content

2. **Configure GitHub Secrets:**
   - Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
   - Add secret: `AZURE_WEBAPP_NAME` = `<your-webapp-name>`
   - Add secret: `AZURE_WEBAPP_PUBLISH_PROFILE` = (paste publish profile content)

3. **Deploy:**
   ```bash
   git add .
   git commit -m "Deploy bot to Azure"
   git push origin main
   ```

4. **Monitor:**
   - Go to **Actions** tab in GitHub
   - Watch the deployment progress

📖 **Full guide:** See [`GITHUB_ACTIONS_SETUP.md`](GITHUB_ACTIONS_SETUP.md) for detailed instructions.

---

### Option 2: Azure CLI (Manual)

**Step 1: Associate Managed Identity to App Service**

**Option A: Azure Portal**
1. Go to: **Azure Portal** → Your **App Service**
2. Left menu: **Settings** → **Identity**
3. Select **User assigned** tab
4. Click **Add (+)**
5. Select your **Managed Identity**
6. Save changes

**Option B: Azure CLI**
```bash
az webapp identity assign \
  --resource-group <your-rg> \
  --name <your-webapp> \
  --identities <managed-identity-resource-id>
```

**Step 2: Configure Environment Variables in Azure**

Use the provided `azure-webapp-settings.json` file:

**Azure Portal:**
1. Go to: **App Service** → **Configuration** → **Application settings**
2. Click **Advanced edit**
3. Paste the content of `azure-webapp-settings.json`
4. Click **OK** → **Save**

**Azure CLI:**
```bash
az webapp config appsettings set \
  --resource-group <your-rg> \
  --name <your-webapp> \
  --settings @azure-webapp-settings.json
```

**Step 3: Configure Messaging Endpoint**

1. Go to: **Azure Portal** → Your **Azure Bot**
2. Left menu: **Settings** → **Configuration**
3. Set **Messaging endpoint**:
   ```
   https://<your-webapp>.azurewebsites.net/api/messages
   ```
4. Click **Apply**

**Step 4: Deploy Code**

**Deploy via Azure CLI:**
```bash
# Create deployment package
cd /workspaces/BotPlusAzureOpenAI
zip -r bot.zip . -x "*.git*" "*__pycache__*" "*.pyc" "*.env"

# Deploy to Azure
az webapp deploy \
  --resource-group <your-rg> \
  --name <your-webapp> \
  --src-path bot.zip \
  --type zip
```

---

### Option 3: Git Deploy

**Push-based deployment from local Git.**

**Configure Git deployment:**
```bash
# Configure Git deployment
az webapp deployment source config-local-git \
  --resource-group <your-rg> \
  --name <your-webapp>

# Get Git URL
GIT_URL=$(az webapp deployment source config-local-git \
  --resource-group <your-rg> \
  --name <your-webapp> \
  --query url \
  --output tsv)

# Push to Azure
git remote add azure $GIT_URL
git push azure main
```

---

### Step 5: Test the Deployment

1. Go to: **Azure Portal** → Your **Azure Bot** → **Test in Web Chat**
2. Send a test message
3. Verify streaming responses

## 📊 Monitoring

### View Logs in Real-Time

**Azure Portal:**
1. Go to: **App Service** → **Monitoring** → **Log stream**

**Azure CLI:**
```bash
az webapp log tail \
  --resource-group <your-rg> \
  --name <your-webapp>
```

### View Metrics

Go to: **App Service** → **Monitoring** → **Metrics**
- Requests
- Response Time
- CPU Usage
- Memory Usage

## 🐛 Troubleshooting

### Error: "401 Unauthorized"

✅ Verify:
- `MicrosoftAppId` matches Managed Identity Client ID
- Managed Identity is associated with App Service
- `MicrosoftAppTenantId` is correct

### Error: "Unauthorized access" (custom message)

✅ Verify:
- `ALLOWED_TENANTS` configuration
- User's tenant ID is in the allowed list
- For testing, leave `ALLOWED_TENANTS` empty

### Bot doesn't respond

✅ Verify:
- Messaging endpoint: `https://<webapp>.azurewebsites.net/api/messages`
- App Service is in "Running" state
- Environment variables configured in Azure
- Check logs for errors

### Error: "ModuleNotFoundError"

✅ Verify:
- Module is in `requirements.txt`
- Re-deploy code
- App Service will install dependencies automatically

## 🔒 Security Best Practices

### 1. Use Azure Key Vault for Secrets

Instead of storing `AZURE_OPENAI_API_KEY` directly:

```bash
# Create Key Vault
az keyvault create \
  --name <keyvault-name> \
  --resource-group <rg>

# Store secret
az keyvault secret set \
  --vault-name <keyvault-name> \
  --name "AzureOpenAIKey" \
  --value "<your-api-key>"

# Configure App Service to use Key Vault
az webapp config appsettings set \
  --resource-group <rg> \
  --name <webapp> \
  --settings AZURE_OPENAI_API_KEY="@Microsoft.KeyVault(SecretUri=https://<keyvault>.vault.azure.net/secrets/AzureOpenAIKey/)"
```

### 2. Enable HTTPS Only

```bash
az webapp update \
  --resource-group <rg> \
  --name <webapp> \
  --set httpsOnly=true
```

### 3. Configure IP Restrictions (optional)

```bash
az webapp config access-restriction add \
  --resource-group <rg> \
  --name <webapp> \
  --rule-name "AllowBotService" \
  --action Allow \
  --ip-address <ip-range> \
  --priority 100
```

## 📝 Deployment Checklist

- [ ] Managed Identity associated with App Service
- [ ] Environment variables configured in Azure
- [ ] Code deployed successfully
- [ ] App Service in "Running" state
- [ ] Messaging endpoint configured in Bot Service
- [ ] Bot tested in "Test in Web Chat"
- [ ] Logs working correctly
- [ ] (Optional) Application Insights configured
- [ ] (Optional) HTTPS Only enabled
- [ ] (Optional) Secrets in Key Vault

## 🔄 Update/Re-deploy

To update the bot after making changes:

```bash
# Option 1: Re-create ZIP and deploy
cd /workspaces/BotPlusAzureOpenAI
zip -r bot.zip . -x "*.git*" "*__pycache__*" "*.pyc" "*.env"
az webapp deploy --resource-group <rg> --name <webapp> --src-path bot.zip --type zip

# Option 2: If using Git deploy
git add .
git commit -m "Update bot"
git push azure main
```

## 📚 Project Structure

```
BotPlusAzureOpenAI/
├── src/
│   ├── agent.py              # Bot logic with multitenant validation
│   ├── main.py               # Application entry point
│   └── start_server.py       # HTTP server
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── azure-webapp-settings.json # Azure App Service settings
└── README.md                # This file
```

## 🧪 Testing

### Local Testing

```bash
# Install Microsoft Agents Playground
npm install -g @microsoft/agents-playground

# Terminal 1: Start bot
python src/start_server.py

# Terminal 2: Start playground
agents-playground \
  --client-id <your-app-id> \
  --tenant-id <your-tenant-id>
```

### Azure Testing

1. Go to: **Azure Portal** → Your **Azure Bot** → **Test in Web Chat**
2. Send test messages
3. Verify streaming responses
4. Check logs in real-time

## 📖 Code Highlights

### Multitenant Validation (`src/agent.py`)

```python
# Optional tenant validation
allowed_tenants_str = environ.get("ALLOWED_TENANTS", "").strip()

if allowed_tenants_str:
    allowed_tenants = [t.strip() for t in allowed_tenants_str.split(",")]
    user_tenant_id = getattr(context.activity.conversation, "tenant_id", None)
    
    if user_tenant_id and user_tenant_id not in allowed_tenants:
        logger.warning(f"Unauthorized tenant access: {user_tenant_id}")
        await context.send_activity(
            "Your organization is not authorized to use this bot."
        )
        return
```

### Streaming Responses (`src/agent.py`)

```python
# Enable streaming
context.streaming_response.set_feedback_loop(True)
context.streaming_response.set_generated_by_ai_label(True)

# Stream from Azure OpenAI
streamed_response = await CLIENT.chat.completions.create(
    model=environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    messages=[...],
    stream=True,
)

async for chunk in streamed_response:
    if chunk.choices and chunk.choices[0].delta.content:
        context.streaming_response.queue_text_chunk(
            chunk.choices[0].delta.content
        )

await context.streaming_response.end_stream()
```

## 🔗 Useful Links

- [Microsoft Agents SDK](https://github.com/microsoft/Agents)
- [Azure Bot Service Docs](https://learn.microsoft.com/en-us/azure/bot-service/)
- [Azure OpenAI Docs](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Managed Identities Docs](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview)

## 📄 License

Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

---

**Built with ❤️ using Microsoft Agents SDK and Azure OpenAI**
