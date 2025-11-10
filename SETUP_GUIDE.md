# 📘 Complete Setup Guide: Azure Bot with OpenAI

This comprehensive guide walks you through creating the entire solution from scratch, including all required Azure resources, networking, security, and Teams manifest deployment.

---

## 🗂️ Table of Contents

1. [Azure Resources Overview](#1-azure-resources-overview)
2. [Prerequisites](#2-prerequisites)
3. [Step 1: Create Resource Group](#3-step-1-create-resource-group)
4. [Step 2: Create Networking Infrastructure](#4-step-2-create-networking-infrastructure)
5. [Step 3: Create User-Assigned Managed Identity](#5-step-3-create-user-assigned-managed-identity)
6. [Step 4: Create Application Insights](#6-step-4-create-application-insights)
7. [Step 5: Deploy AI Foundry and Azure OpenAI](#7-step-5-deploy-ai-foundry-and-azure-openai)
8. [Step 6: Create App Service](#8-step-6-create-app-service)
9. [Step 7: Create Azure Bot Service](#9-step-7-create-azure-bot-service)
10. [Step 8: Configure and Deploy Application Code](#10-step-8-configure-and-deploy-application-code)
11. [Step 9: Create and Deploy Teams Manifest](#11-step-9-create-and-deploy-teams-manifest)
12. [Step 10: Testing and Validation](#12-step-10-testing-and-validation)
13. [Troubleshooting](#troubleshooting)
14. [Monitoring and Maintenance](#monitoring-and-maintenance)

---

## 1. 🗂️ Azure Resources Overview

To deploy this solution, you will need the following Azure resources:

### Required Resources

| Resource | Purpose | Notes |
|----------|---------|-------|
| **Resource Group** | Container for all resources | Organizes and manages the solution |
| **User-Assigned Managed Identity** | Authentication for Bot Service | No passwords/secrets required |
| **Azure Bot Service** | Bot Framework endpoint | Must be configured with Managed Identity |
| **App Service** | Hosts the Python proxy application | Connects Bot Framework with Azure OpenAI |
| **App Service Plan** | Compute resources for App Service | Linux-based, Python 3.10+ |
| **AI Foundry Hub** | AI project workspace | Manages AI models and deployments |
| **Azure OpenAI** | AI model deployment | Requires at least one deployed model (e.g., GPT-4) |
| **Application Insights** | Monitoring and logging | Tracks performance and errors |

### Optional Resources (for Production)

| Resource | Purpose | Notes |
|----------|---------|-------|
| **Virtual Network (VNet)** | Network isolation | Secures communication between services |
| **Subnets** | Network segmentation | Separate subnets for App Service, OpenAI, etc. |
| **Private Endpoints** | Private connectivity | Removes public internet exposure |
| **Key Vault** | Secret management | Stores API keys securely |
| **NAT Gateway** | Outbound connectivity | For VNet-integrated App Service |

### Alternative Deployment Options

> **Note**: This guide uses **Azure App Service** for simplicity. You can also use:
> - **Azure Container Apps (ACA)**: For containerized workloads
> - **Azure Kubernetes Service (AKS)**: For advanced orchestration
> - **Azure Functions**: For serverless deployments
> 
> The core concepts remain the same—only the hosting platform changes.

---

## 2. 📋 Prerequisites

### Azure Subscription Requirements
- ✅ Active Azure subscription
- ✅ Permissions to create resources (Contributor role or higher)
- ✅ Azure OpenAI access approved (requires application)
- ✅ Sufficient quota for chosen region

### Development Tools
- ✅ [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) installed
- ✅ [Python 3.10+](https://www.python.org/downloads/) installed
- ✅ [Git](https://git-scm.com/) (optional, for version control)
- ✅ Text editor (VS Code recommended)

### Microsoft Teams Access
- ✅ Microsoft 365 tenant with Teams enabled
- ✅ Permissions to sideload custom apps (Teams admin role)
- ✅ Developer mode enabled in Teams

### Knowledge Prerequisites
- Basic understanding of Azure resources
- Familiarity with command line/terminal
- Basic Python knowledge (for code customization)

---

## 3. 🚀 Step 1: Create Resource Group

A resource group is a container that holds related Azure resources.

### Via Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **Resource groups** → **Create**
3. Fill in the details:
   - **Subscription**: Select your subscription
   - **Resource group**: `rg-bot-openai-prod`
   - **Region**: `Sweden Central` (or your preferred region)
4. Click **Review + create** → **Create**

### Via Azure CLI

```bash
# Login to Azure
az login

# Set variables
RESOURCE_GROUP="rg-bot-openai-prod"
LOCATION="swedencentral"

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

✅ **Verification**: Run `az group show --name $RESOURCE_GROUP` to confirm creation.

---

## 4. 🌐 Step 2: Create Networking Infrastructure

This step creates a secure network for your resources. **Skip this section if you want a simple public deployment.**

### Why Networking?

- **Security**: Keeps traffic private within Azure
- **Compliance**: Meets enterprise security requirements
- **Control**: Restricts access to authorized services only

### Architecture Overview

```
VNet: 10.0.0.0/16
├── Subnet 1: AppServiceSubnet (10.0.1.0/24)     ← App Service integration
├── Subnet 2: PrivateEndpointSubnet (10.0.2.0/24) ← Private endpoints
└── Subnet 3: OpenAISubnet (10.0.3.0/24)         ← Azure OpenAI private endpoint
```

### Create VNet and Subnets

```bash
# Set variables
VNET_NAME="vnet-bot-openai"
VNET_ADDRESS_PREFIX="10.0.0.0/16"
APPSERVICE_SUBNET="AppServiceSubnet"
APPSERVICE_SUBNET_PREFIX="10.0.1.0/24"
PE_SUBNET="PrivateEndpointSubnet"
PE_SUBNET_PREFIX="10.0.2.0/24"
OPENAI_SUBNET="OpenAISubnet"
OPENAI_SUBNET_PREFIX="10.0.3.0/24"

# Create VNet
az network vnet create \
  --resource-group $RESOURCE_GROUP \
  --name $VNET_NAME \
  --address-prefix $VNET_ADDRESS_PREFIX \
  --location $LOCATION

# Create App Service subnet (with delegation)
az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $APPSERVICE_SUBNET \
  --address-prefix $APPSERVICE_SUBNET_PREFIX \
  --delegations Microsoft.Web/serverFarms

# Create Private Endpoint subnet
az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $PE_SUBNET \
  --address-prefix $PE_SUBNET_PREFIX \
  --disable-private-endpoint-network-policies true

# Create Azure OpenAI subnet
az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $OPENAI_SUBNET \
  --address-prefix $OPENAI_SUBNET_PREFIX
```

### Create NAT Gateway (for outbound connectivity)

```bash
NAT_GATEWAY_NAME="nat-bot-openai"
PUBLIC_IP_NAME="pip-nat-bot-openai"

# Create public IP for NAT
az network public-ip create \
  --resource-group $RESOURCE_GROUP \
  --name $PUBLIC_IP_NAME \
  --sku Standard \
  --location $LOCATION

# Create NAT Gateway
az network nat gateway create \
  --resource-group $RESOURCE_GROUP \
  --name $NAT_GATEWAY_NAME \
  --public-ip-addresses $PUBLIC_IP_NAME \
  --location $LOCATION

# Associate NAT Gateway with App Service subnet
az network vnet subnet update \
  --resource-group $RESOURCE_GROUP \
  --vnet-name $VNET_NAME \
  --name $APPSERVICE_SUBNET \
  --nat-gateway $NAT_GATEWAY_NAME
```

✅ **Verification**: Run `az network vnet show --name $VNET_NAME --resource-group $RESOURCE_GROUP`

---

## 5. 🔐 Step 3: Create User-Assigned Managed Identity

Managed Identity eliminates the need for passwords and secrets.

### Why Managed Identity?

- ✅ **No credentials to manage**: Azure handles authentication automatically
- ✅ **Microsoft recommended**: Best practice for production workloads
- ✅ **Secure**: Cannot be accidentally leaked or compromised

### Create Managed Identity

#### Via Azure Portal

1. Go to **Azure Portal** → Search for **Managed Identities**
2. Click **Create**
3. Fill in details:
   - **Subscription**: Your subscription
   - **Resource group**: `rg-bot-openai-prod`
   - **Region**: `Sweden Central`
   - **Name**: `id-bot-openai`
4. Click **Review + create** → **Create**
5. **Copy the Client ID** (you'll need it later)

#### Via Azure CLI

```bash
MANAGED_IDENTITY_NAME="id-bot-openai"

# Create managed identity
az identity create \
  --resource-group $RESOURCE_GROUP \
  --name $MANAGED_IDENTITY_NAME \
  --location $LOCATION

# Get Client ID and Principal ID
MANAGED_IDENTITY_CLIENT_ID=$(az identity show \
  --resource-group $RESOURCE_GROUP \
  --name $MANAGED_IDENTITY_NAME \
  --query clientId \
  --output tsv)

MANAGED_IDENTITY_PRINCIPAL_ID=$(az identity show \
  --resource-group $RESOURCE_GROUP \
  --name $MANAGED_IDENTITY_NAME \
  --query principalId \
  --output tsv)

echo "Client ID: $MANAGED_IDENTITY_CLIENT_ID"
echo "Principal ID: $MANAGED_IDENTITY_PRINCIPAL_ID"
```

**📝 Important**: Save the `Client ID`—you'll need it for Bot Service and App Service configuration.

✅ **Verification**: The Client ID should be a GUID like `76c95995-d563-4075-a103-25d96fcc3e1b`

---

## 6. 📊 Step 4: Create Application Insights

Application Insights provides monitoring, logging, and telemetry for your bot.

### Why Application Insights?

- **Real-time monitoring**: Track requests, failures, and performance
- **Distributed tracing**: Follow requests across services
- **Alerts**: Get notified of issues automatically
- **Analytics**: Query logs and metrics

### Create Application Insights

#### Via Azure Portal

1. Search for **Application Insights** → **Create**
2. Fill in details:
   - **Resource group**: `rg-bot-openai-prod`
   - **Name**: `appi-bot-openai`
   - **Region**: `Sweden Central`
   - **Workspace**: Create new Log Analytics workspace
3. Click **Review + create** → **Create**
4. **Copy the Connection String** (under **Overview** → **Connection String**)

#### Via Azure CLI

```bash
APP_INSIGHTS_NAME="appi-bot-openai"

# Create Application Insights
az monitor app-insights component create \
  --app $APP_INSIGHTS_NAME \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --application-type web

# Get Connection String
APP_INSIGHTS_CONNECTION_STRING=$(az monitor app-insights component show \
  --app $APP_INSIGHTS_NAME \
  --resource-group $RESOURCE_GROUP \
  --query connectionString \
  --output tsv)

echo "Connection String: $APP_INSIGHTS_CONNECTION_STRING"
```

**📝 Important**: Save the connection string for App Service configuration.

---

## 7. 🤖 Step 5: Deploy AI Foundry and Azure OpenAI

AI Foundry is Microsoft's platform for managing AI models and deployments.

### 5.1 Create AI Foundry Hub

#### Via Azure Portal

1. Go to [AI Foundry Portal](https://ai.azure.com)
2. Click **Create new hub**
3. Fill in details:
   - **Hub name**: `aih-bot-openai`
   - **Subscription**: Your subscription
   - **Resource group**: `rg-bot-openai-prod`
   - **Region**: `Sweden Central`
4. Click **Create**

#### Via Azure CLI

```bash
# Note: AI Foundry Hub creation requires the Azure ML extension
az extension add --name ml

HUB_NAME="aih-bot-openai"

az ml workspace create \
  --kind hub \
  --resource-group $RESOURCE_GROUP \
  --name $HUB_NAME \
  --location $LOCATION
```

### 5.2 Create AI Foundry Project

1. In AI Foundry Portal, select your hub
2. Click **Create project**
3. Fill in details:
   - **Project name**: `aip-bot-openai`
   - **Hub**: Select your hub
4. Click **Create**

### 5.3 Deploy Azure OpenAI Service

#### Via Azure Portal

1. Search for **Azure OpenAI** → **Create**
2. Fill in details:
   - **Resource group**: `rg-bot-openai-prod`
   - **Region**: `Sweden Central`
   - **Name**: `oai-bot-openai` (must be globally unique)
   - **Pricing tier**: Standard S0
3. **Networking** (optional for secure setup):
   - Select **Selected networks and private endpoints**
   - Add private endpoint in `OpenAISubnet`
4. Click **Review + create** → **Create**

#### Via Azure CLI

```bash
OPENAI_NAME="oai-bot-openai-$(date +%s)"  # Add timestamp for uniqueness

# Create Azure OpenAI resource
az cognitiveservices account create \
  --name $OPENAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --kind OpenAI \
  --sku S0 \
  --location $LOCATION \
  --custom-domain $OPENAI_NAME \
  --yes

# Get endpoint and key
OPENAI_ENDPOINT=$(az cognitiveservices account show \
  --name $OPENAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.endpoint \
  --output tsv)

OPENAI_KEY=$(az cognitiveservices account keys list \
  --name $OPENAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --query key1 \
  --output tsv)

echo "OpenAI Endpoint: $OPENAI_ENDPOINT"
echo "OpenAI Key: $OPENAI_KEY"
```

### 5.4 Deploy a Model

You need at least one deployed model (e.g., GPT-4, GPT-4o).

#### Via Azure Portal

1. Go to **Azure OpenAI Studio**: https://oai.azure.com
2. Select your resource: `oai-bot-openai`
3. Click **Deployments** → **Create new deployment**
4. Fill in details:
   - **Model**: `gpt-4o` (or latest available)
   - **Deployment name**: `gpt-4o-deployment`
   - **Deployment type**: Standard
   - **Tokens per minute rate limit**: 50K (or as needed)
5. Click **Create**

#### Via Azure CLI

```bash
DEPLOYMENT_NAME="gpt-4o-deployment"
MODEL_NAME="gpt-4o"
MODEL_VERSION="2024-08-06"  # Check latest version in Azure Portal

az cognitiveservices account deployment create \
  --resource-group $RESOURCE_GROUP \
  --name $OPENAI_NAME \
  --deployment-name $DEPLOYMENT_NAME \
  --model-name $MODEL_NAME \
  --model-version $MODEL_VERSION \
  --model-format OpenAI \
  --sku-name Standard \
  --sku-capacity 50
```

**📝 Important**: Save these values:
- `OPENAI_ENDPOINT`: e.g., `https://oai-bot-openai.openai.azure.com/`
- `OPENAI_KEY`: Your API key
- `DEPLOYMENT_NAME`: e.g., `gpt-4o-deployment`

✅ **Verification**: Go to Azure OpenAI Studio → **Deployments** and confirm the model is running.

---

## 8. 🌐 Step 6: Create App Service

App Service hosts your Python bot application.

### 6.1 Create App Service Plan

```bash
APP_SERVICE_PLAN="asp-bot-openai"
APP_SERVICE_NAME="app-bot-openai-$(date +%s)"  # Unique name

# Create App Service Plan (Linux, Python)
az appservice plan create \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_PLAN \
  --location $LOCATION \
  --is-linux \
  --sku B1  # Use P1V2 or higher for production
```

### 6.2 Create App Service

```bash
# Create Web App with Python 3.11
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan $APP_SERVICE_PLAN \
  --name $APP_SERVICE_NAME \
  --runtime "PYTHON:3.11"

# Enable HTTPS only
az webapp update \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_NAME \
  --set httpsOnly=true

# Configure startup command
az webapp config set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_NAME \
  --startup-file "python -m src.main"

echo "App Service URL: https://${APP_SERVICE_NAME}.azurewebsites.net"
```

### 6.3 Assign Managed Identity to App Service

```bash
# Get Managed Identity resource ID
MANAGED_IDENTITY_ID=$(az identity show \
  --resource-group $RESOURCE_GROUP \
  --name $MANAGED_IDENTITY_NAME \
  --query id \
  --output tsv)

# Assign to App Service
az webapp identity assign \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_NAME \
  --identities $MANAGED_IDENTITY_ID
```

### 6.4 Configure VNet Integration (Optional)

**Skip this if not using VNet.**

```bash
# Integrate App Service with VNet
az webapp vnet-integration add \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_NAME \
  --vnet $VNET_NAME \
  --subnet $APPSERVICE_SUBNET

# Enable route-all traffic through VNet
az webapp config set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_NAME \
  --generic-configurations '{"vnetRouteAllEnabled": true}'
```

### 6.5 Grant Managed Identity Access to Azure OpenAI

```bash
# Get OpenAI resource ID
OPENAI_RESOURCE_ID=$(az cognitiveservices account show \
  --name $OPENAI_NAME \
  --resource-group $RESOURCE_GROUP \
  --query id \
  --output tsv)

# Assign "Cognitive Services OpenAI User" role
az role assignment create \
  --assignee $MANAGED_IDENTITY_PRINCIPAL_ID \
  --role "Cognitive Services OpenAI User" \
  --scope $OPENAI_RESOURCE_ID
```

**📝 Important**: Save the App Service URL: `https://<app-name>.azurewebsites.net`

---

## 9. 🤖 Step 7: Create Azure Bot Service

Azure Bot Service provides the Bot Framework channel endpoint.

### 7.1 Create Bot Service

#### Via Azure Portal

1. Search for **Azure Bot** → **Create**
2. Fill in details:
   - **Bot handle**: `bot-openai-proxy` (unique name)
   - **Subscription**: Your subscription
   - **Resource group**: `rg-bot-openai-prod`
   - **Pricing tier**: Standard S1
   - **Type of App**: **User-Assigned Managed Identity**
   - **App ID**: Select `id-bot-openai`
   - **Tenant ID**: Your Azure AD tenant ID
3. Click **Review + create** → **Create**

#### Via Azure CLI

```bash
BOT_NAME="bot-openai-proxy"
TENANT_ID=$(az account show --query tenantId --output tsv)

# Create Azure Bot with Managed Identity
az bot create \
  --resource-group $RESOURCE_GROUP \
  --name $BOT_NAME \
  --kind azurebot \
  --app-type UserAssignedMSI \
  --tenant-id $TENANT_ID \
  --msi-resource-id $MANAGED_IDENTITY_ID \
  --location global
```

### 7.2 Configure Messaging Endpoint

The messaging endpoint tells Bot Framework where to send messages.

```bash
# Set messaging endpoint
MESSAGING_ENDPOINT="https://${APP_SERVICE_NAME}.azurewebsites.net/api/messages"

az bot update \
  --resource-group $RESOURCE_GROUP \
  --name $BOT_NAME \
  --endpoint $MESSAGING_ENDPOINT
```

**📝 Format**: `https://<your-app-service>.azurewebsites.net/api/messages`

### 7.3 Enable Microsoft Teams Channel

#### Via Azure Portal

1. Go to **Azure Bot** → **Channels**
2. Click **Microsoft Teams** icon
3. Accept the terms
4. Click **Apply**

#### Via Azure CLI

```bash
# Enable Teams channel
az bot msteams create \
  --resource-group $RESOURCE_GROUP \
  --name $BOT_NAME
```

✅ **Verification**: Go to **Azure Bot** → **Test in Web Chat** (may not work until app is deployed).

---

## 10. 💻 Step 8: Configure and Deploy Application Code

Now we'll configure environment variables and deploy the Python code.

### 8.1 Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/BotPlusAzureOpenAI.git
cd BotPlusAzureOpenAI
```

### 8.2 Configure Environment Variables in App Service

You need to configure these settings in your App Service:

| Variable | Value | Description |
|----------|-------|-------------|
| `MicrosoftAppType` | `UserAssignedMSI` | Authentication type |
| `MicrosoftAppId` | `<client-id>` | Managed Identity Client ID |
| `MicrosoftAppPassword` | `` (empty) | Leave blank for Managed Identity |
| `MicrosoftAppTenantId` | `<tenant-id>` | Your Azure AD tenant ID |
| `ALLOWED_TENANTS` | `` or `<tenant-ids>` | Comma-separated tenant IDs (optional) |
| `AZURE_OPENAI_API_VERSION` | `2024-02-15-preview` | API version |
| `AZURE_OPENAI_ENDPOINT` | `https://oai-xxx.openai.azure.com/` | Your OpenAI endpoint |
| `AZURE_OPENAI_API_KEY` | `<your-key>` | Your OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | `gpt-4o-deployment` | Your deployment name |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | `<connection-string>` | Application Insights connection string |

#### Option A: Using Azure Portal

1. Go to **App Service** → **Configuration** → **Application settings**
2. Click **New application setting** for each variable
3. Click **Save**

#### Option B: Using Azure CLI

```bash
# Configure all settings at once
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_NAME \
  --settings \
    MicrosoftAppType="UserAssignedMSI" \
    MicrosoftAppId="$MANAGED_IDENTITY_CLIENT_ID" \
    MicrosoftAppPassword="" \
    MicrosoftAppTenantId="$TENANT_ID" \
    ALLOWED_TENANTS="" \
    AZURE_OPENAI_API_VERSION="2024-02-15-preview" \
    AZURE_OPENAI_ENDPOINT="$OPENAI_ENDPOINT" \
    AZURE_OPENAI_API_KEY="$OPENAI_KEY" \
    AZURE_OPENAI_DEPLOYMENT_NAME="$DEPLOYMENT_NAME" \
    APPLICATIONINSIGHTS_CONNECTION_STRING="$APP_INSIGHTS_CONNECTION_STRING"
```

#### Option C: Using JSON File

The repository includes `azure-webapp-settings.json`. Update it with your values:

```json
[
  {
    "name": "MicrosoftAppType",
    "value": "UserAssignedMSI",
    "slotSetting": false
  },
  {
    "name": "MicrosoftAppId",
    "value": "YOUR_MANAGED_IDENTITY_CLIENT_ID",
    "slotSetting": false
  },
  {
    "name": "AZURE_OPENAI_ENDPOINT",
    "value": "https://YOUR_OPENAI_RESOURCE.openai.azure.com/",
    "slotSetting": false
  }
  // ... etc
]
```

Then apply:

```bash
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_NAME \
  --settings @azure-webapp-settings.json
```

### 8.3 Deploy Application Code

#### Option 1: ZIP Deployment (Quickest)

```bash
# Create deployment package
zip -r bot.zip . -x "*.git*" "*__pycache__*" "*.pyc" "*.env" "botmanifest/*"

# Deploy to Azure
az webapp deploy \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_NAME \
  --src-path bot.zip \
  --type zip

# Clean up
rm bot.zip
```

#### Option 2: GitHub Actions (Recommended for CI/CD)

See the existing `.github/workflows/deploy-to-azure.yml` file. You need to:

1. Add GitHub secrets:
   - `AZURE_WEBAPP_NAME`: Your App Service name
   - `AZURE_WEBAPP_PUBLISH_PROFILE`: Download from Azure Portal
2. Push to `main` branch—deployment happens automatically

#### Option 3: Local Git Deployment

```bash
# Configure Git deployment
az webapp deployment source config-local-git \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_NAME

# Get Git URL
GIT_URL=$(az webapp deployment list-publishing-credentials \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_NAME \
  --query scmUri \
  --output tsv)

# Add Azure remote
git remote add azure $GIT_URL

# Deploy
git push azure main
```

### 8.4 Verify Deployment

```bash
# Check deployment logs
az webapp log tail \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_NAME
```

✅ **Verification**: 
- Go to `https://<app-service-name>.azurewebsites.net` → should return a response
- Check logs for errors
- App Service should show **Running** status

---

## 11. 📱 Step 9: Create and Deploy Teams Manifest

The Teams manifest configures how your bot appears in Microsoft Teams.

### 9.1 Prepare the Manifest File

The repository includes `botmanifest/manifest.example.json`. You need to customize it.

#### Step 1: Copy the Example

```bash
cp botmanifest/manifest.example.json botmanifest/manifest.json
```

#### Step 2: Update Required Fields

Edit `botmanifest/manifest.json` and replace these placeholders:

| Field | Example Value | Where to Find |
|-------|---------------|---------------|
| `id` | `b8c8f73a-1111-2222-3333-444444444444` | Generate a new GUID at [guidgen.com](https://www.guidgen.com/) |
| `packageName` | `com.yourcompany.botproxy` | Your reverse domain name |
| `name.short` | `My AI Bot` | Display name in Teams (max 30 chars) |
| `name.full` | `My AI Bot with Azure OpenAI` | Full name (max 100 chars) |
| `description.short` | `AI-powered bot assistant` | Short description (max 80 chars) |
| `description.full` | `Full description of your bot capabilities...` | Detailed description (max 4000 chars) |
| `developer.name` | `Your Company Name` | Your organization name |
| `developer.websiteUrl` | `https://yourcompany.com` | Your website URL |
| `developer.privacyUrl` | `https://yourcompany.com/privacy` | Privacy policy URL |
| `developer.termsOfUseUrl` | `https://yourcompany.com/terms` | Terms of use URL |
| `bots[0].botId` | `76c95995-xxxx-xxxx-xxxx-xxxxxxxxxxxx` | **Managed Identity Client ID** |
| `validDomains[0]` | `app-bot-openai-xxx.azurewebsites.net` | Your App Service hostname (without `https://`) |

#### Example Completed Manifest

```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
  "manifestVersion": "1.16",
  "version": "1.0.0",
  "id": "b8c8f73a-5678-9abc-def0-123456789abc",
  "packageName": "com.contoso.aibot",
  "name": {
    "short": "Contoso AI Bot",
    "full": "Contoso AI Assistant powered by Azure OpenAI"
  },
  "description": {
    "short": "AI-powered assistant for your team",
    "full": "An intelligent bot that uses Azure OpenAI to answer questions and assist with tasks."
  },
  "developer": {
    "name": "Contoso Corporation",
    "websiteUrl": "https://contoso.com",
    "privacyUrl": "https://contoso.com/privacy",
    "termsOfUseUrl": "https://contoso.com/terms"
  },
  "icons": {
    "color": "color.png",
    "outline": "outline.png"
  },
  "accentColor": "#6264A7",
  "bots": [
    {
      "botId": "76c95995-d563-4075-a103-25d96fcc3e1b",
      "scopes": ["personal"],
      "supportsFiles": false,
      "isNotificationOnly": false
    }
  ],
  "permissions": ["identity"],
  "validDomains": [
    "app-bot-openai-1234567890.azurewebsites.net"
  ]
}
```

**⚠️ Critical Fields:**
- `bots[0].botId`: **Must match your Managed Identity Client ID**
- `validDomains`: **Must match your App Service hostname** (no `https://` or trailing `/`)

### 9.2 Add Icons

The manifest requires two icon files:

| File | Size | Format | Description |
|------|------|--------|-------------|
| `color.png` | 192x192 px | PNG | Full-color icon |
| `outline.png` | 32x32 px | PNG | White transparent outline |

Place these files in the `botmanifest/` folder.

**Quick Option**: Use placeholder icons from [Microsoft Teams samples](https://github.com/OfficeDev/Microsoft-Teams-Samples/tree/main/samples/bot-conversation/nodejs/appPackage).

### 9.3 Create the App Package

```bash
# Navigate to manifest folder
cd botmanifest

# Create ZIP package (must be named .zip, not .appx)
zip manifest.zip manifest.json color.png outline.png

# Verify contents
unzip -l manifest.zip
```

**✅ Required files in ZIP:**
- `manifest.json`
- `color.png`
- `outline.png`

### 9.4 Upload to Teams (Sideloading)

#### Prerequisites

1. Enable custom app sideloading (Teams Admin):
   - Go to [Teams Admin Center](https://admin.teams.microsoft.com)
   - Navigate to **Teams apps** → **Setup policies**
   - Enable **Upload custom apps**

2. Enable developer mode in Teams:
   - Open **Teams** → **Settings** → **About**
   - Click version number 7 times to enable **Developer preview**

#### Upload the App

1. Open **Microsoft Teams**
2. Click **Apps** (left sidebar)
3. Click **Manage your apps** (bottom left)
4. Click **Upload an app** → **Upload a custom app**
5. Select `manifest.zip`
6. Click **Add** to install for yourself
   - Or **Add to a team** to install for a team

### 9.5 Verify Installation

1. Go to **Teams** → **Chat**
2. Click **New chat**
3. Search for your bot name (e.g., "Contoso AI Bot")
4. Send a test message: "Hello"
5. You should receive a streaming response from Azure OpenAI

✅ **Verification**: The bot responds with AI-generated messages.

---

## 12. ✅ Step 10: Testing and Validation

### 12.1 Test Bot in Web Chat

1. Go to **Azure Portal** → **Azure Bot** → **Test in Web Chat**
2. Send a message: "What can you help me with?"
3. Verify you receive a streaming response

### 12.2 Test Bot in Microsoft Teams

1. Open **Teams** → Find your bot
2. Send various messages:
   - "Explain quantum computing"
   - "Write a Python function to sort a list"
   - "What's the weather like?" (if you add tools)
3. Verify responses are relevant and stream properly

### 12.3 Test Multitenant Validation (if configured)

If you set `ALLOWED_TENANTS`:

1. Test from an **allowed tenant**: Should work ✅
2. Test from a **blocked tenant**: Should receive "Unauthorized" message ❌

### 12.4 Monitor Logs

```bash
# Real-time logs
az webapp log tail \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_NAME

# Download logs
az webapp log download \
  --resource-group $RESOURCE_GROUP \
  --name $APP_SERVICE_NAME \
  --log-file bot-logs.zip
```

### 12.5 Check Application Insights

1. Go to **Application Insights** → **Live Metrics**
2. Send a message in Teams
3. Watch requests appear in real-time
4. Check for errors or performance issues

---

## 🐛 Troubleshooting

### Issue: "401 Unauthorized" Error

**Symptoms**: Bot doesn't respond, logs show authentication errors.

**Solutions**:
1. Verify Managed Identity Client ID matches in:
   - Bot Service configuration
   - App Service environment variables (`MicrosoftAppId`)
   - Teams manifest (`bots[0].botId`)
2. Ensure Managed Identity is assigned to App Service
3. Check `MicrosoftAppTenantId` is correct
4. Verify messaging endpoint: `https://<app-service>.azurewebsites.net/api/messages`

### Issue: "Unauthorized access" Message in Chat

**Symptoms**: Bot responds with "Your organization is not authorized..."

**Solutions**:
1. Check `ALLOWED_TENANTS` configuration
2. Get user's tenant ID:
   ```bash
   az account show --query tenantId --output tsv
   ```
3. Add tenant ID to `ALLOWED_TENANTS` (comma-separated)
4. For testing, set `ALLOWED_TENANTS=""` (empty = allow all)

### Issue: Bot Doesn't Respond

**Symptoms**: Messages sent but no response.

**Solutions**:
1. Check App Service is running:
   ```bash
   az webapp show --resource-group $RESOURCE_GROUP --name $APP_SERVICE_NAME --query state
   ```
2. Verify messaging endpoint in Bot Service
3. Check logs for errors:
   ```bash
   az webapp log tail --resource-group $RESOURCE_GROUP --name $APP_SERVICE_NAME
   ```
4. Test endpoint directly:
   ```bash
   curl https://<app-service>.azurewebsites.net/api/messages
   ```

### Issue: "ModuleNotFoundError" in Logs

**Symptoms**: Logs show Python import errors.

**Solutions**:
1. Verify `requirements.txt` is complete
2. Check startup command: `python -m src.main`
3. Redeploy application
4. Verify Python version: `3.11` (Linux App Service)

### Issue: Azure OpenAI Errors

**Symptoms**: Logs show OpenAI API errors.

**Solutions**:
1. Verify deployment name is correct
2. Check API key is valid
3. Verify endpoint URL format: `https://<resource>.openai.azure.com/`
4. Check quota/rate limits in Azure OpenAI
5. If using private endpoints, verify VNet integration

### Issue: Teams Manifest Upload Fails

**Symptoms**: "Invalid app package" error.

**Solutions**:
1. Verify ZIP contains exactly 3 files: `manifest.json`, `color.png`, `outline.png`
2. Check manifest schema version: `1.16`
3. Validate `botId` is a valid GUID
4. Verify `validDomains` format (no `https://` or trailing `/`)
5. Use [Teams App Validator](https://dev.teams.microsoft.com/appvalidation.html)

### Issue: VNet Integration Problems

**Symptoms**: App Service can't reach Azure OpenAI.

**Solutions**:
1. Verify subnet delegation: `Microsoft.Web/serverFarms`
2. Check NSG rules allow outbound traffic
3. Verify NAT Gateway is attached
4. Enable route-all: `vnetRouteAllEnabled: true`
5. Check private endpoint DNS resolution

---

## 📊 Monitoring and Maintenance

### Daily Monitoring

**Application Insights Dashboard**:
1. Go to **Application Insights** → **Overview**
2. Monitor:
   - Request rate
   - Failed requests
   - Response time
   - Exceptions

**Key Metrics to Watch**:
- **Requests**: Should be consistent with usage
- **Failures**: Should be < 1%
- **Response time**: Should be < 2s for bot responses
- **Exceptions**: Investigate any spikes

### Set Up Alerts

```bash
# Alert on high failure rate
az monitor metrics alert create \
  --name "Bot High Failure Rate" \
  --resource-group $RESOURCE_GROUP \
  --scopes $(az webapp show --resource-group $RESOURCE_GROUP --name $APP_SERVICE_NAME --query id --output tsv) \
  --condition "avg requests/failed > 10" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email your-email@example.com
```

### Regular Maintenance

**Weekly**:
- Review Application Insights for errors
- Check App Service logs for warnings
- Verify Azure OpenAI quota usage

**Monthly**:
- Update Python dependencies (`pip list --outdated`)
- Review security advisories
- Check Azure OpenAI for new model versions
- Review cost reports

**Quarterly**:
- Update manifest version and republish
- Review and update documentation
- Perform disaster recovery drills
- Update bot responses/prompts

### Cost Optimization

**Monitor Costs**:
1. Go to **Cost Management** → **Cost analysis**
2. Filter by resource group: `rg-bot-openai-prod`
3. Identify top spending resources

**Optimization Tips**:
- Use **B1** App Service tier for dev/test
- Use **P1V2+** for production (required for VNet)
- Monitor Azure OpenAI token usage
- Configure auto-scaling for App Service
- Use reserved instances for predictable workloads

### Backup and Disaster Recovery

**What to Backup**:
- Application code (Git repository)
- Environment variables (export settings)
- Teams manifest and icons
- Azure resource configurations

**Disaster Recovery Plan**:
1. Document all resource IDs and configurations
2. Store infrastructure-as-code (ARM templates/Bicep)
3. Test restoration in a separate subscription
4. Maintain runbooks for common scenarios

---

## 📚 Additional Resources

### Microsoft Documentation
- [Azure Bot Service](https://learn.microsoft.com/azure/bot-service/)
- [Microsoft Agents SDK](https://github.com/microsoft/Agents)
- [Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/)
- [Managed Identities](https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/)
- [Teams App Development](https://learn.microsoft.com/microsoftteams/platform/)

### Sample Code and Templates
- [Bot Framework Samples](https://github.com/microsoft/BotBuilder-Samples)
- [Teams App Samples](https://github.com/OfficeDev/Microsoft-Teams-Samples)
- [Azure Quickstart Templates](https://github.com/Azure/azure-quickstart-templates)

### Tools
- [Bot Framework Emulator](https://github.com/Microsoft/BotFramework-Emulator)
- [Teams App Validator](https://dev.teams.microsoft.com/appvalidation.html)
- [Azure Resource Graph Explorer](https://portal.azure.com/#blade/HubsExtension/ArgQueryBlade)

---

## 🎯 Deployment Checklist

Use this checklist to ensure all steps are completed:

### Azure Resources
- [ ] Resource group created
- [ ] (Optional) VNet and subnets created
- [ ] (Optional) NAT Gateway configured
- [ ] User-Assigned Managed Identity created
- [ ] Application Insights created
- [ ] AI Foundry Hub and Project created
- [ ] Azure OpenAI resource deployed
- [ ] Azure OpenAI model deployed (e.g., GPT-4o)
- [ ] App Service Plan created
- [ ] App Service created
- [ ] Managed Identity assigned to App Service
- [ ] (Optional) VNet integration configured
- [ ] Azure Bot Service created
- [ ] Teams channel enabled

### Configuration
- [ ] App Service environment variables configured
- [ ] Messaging endpoint set in Bot Service
- [ ] Managed Identity granted access to Azure OpenAI
- [ ] Application Insights connection string configured
- [ ] (Optional) Tenant allow-list configured

### Application Deployment
- [ ] Repository cloned
- [ ] Code deployed to App Service
- [ ] App Service is running
- [ ] Logs show no errors
- [ ] Endpoint responds to HTTP requests

### Teams Manifest
- [ ] Manifest file customized
- [ ] Bot ID matches Managed Identity Client ID
- [ ] Valid domains configured correctly
- [ ] Icons created (192x192 and 32x32)
- [ ] App package created (manifest.zip)
- [ ] App uploaded to Teams
- [ ] Bot installed and tested

### Testing
- [ ] Bot responds in Web Chat
- [ ] Bot responds in Teams
- [ ] Streaming works correctly
- [ ] (Optional) Multitenant validation tested
- [ ] Application Insights shows telemetry
- [ ] No errors in logs

### Production Readiness
- [ ] HTTPS Only enabled
- [ ] Secrets moved to Key Vault (optional)
- [ ] Alerts configured
- [ ] Monitoring dashboard created
- [ ] Backup and recovery plan documented
- [ ] Cost optimization reviewed

---

**🎉 Congratulations!** Your multitenant Azure OpenAI bot is now fully deployed and ready for production use!

For questions or issues, refer to the [Troubleshooting](#troubleshooting) section or consult the [Microsoft Documentation](https://learn.microsoft.com/azure/bot-service/).
