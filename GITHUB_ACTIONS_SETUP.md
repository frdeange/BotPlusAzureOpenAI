# 🚀 GitHub Actions Deployment Guide

This guide explains how to configure GitHub Actions to automatically deploy your bot to Azure Web App.

## 📋 Prerequisites

- ✅ Azure Web App created
- ✅ GitHub repository with your bot code
- ✅ Admin access to your GitHub repository

## 🔐 Step 1: Get Azure Web App Publish Profile

### Option A: Azure Portal (Recommended)

1. Go to **Azure Portal** → Your **Web App**
2. Click **Get publish profile** (top menu bar)
3. Save the downloaded `.PublishSettings` file
4. Open the file and **copy all its content**

### Option B: Azure CLI

```bash
az webapp deployment list-publishing-profiles \
  --resource-group <your-resource-group> \
  --name <your-webapp-name> \
  --xml
```

Copy the entire XML output.

## 🔑 Step 2: Configure GitHub Secrets

1. Go to your **GitHub repository**
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these secrets:

### Secret 1: AZURE_WEBAPP_NAME

- **Name**: `AZURE_WEBAPP_NAME`
- **Value**: `<your-webapp-name>` (e.g., `my-bot-webapp`)
- Click **Add secret**

### Secret 2: AZURE_WEBAPP_PUBLISH_PROFILE

- **Name**: `AZURE_WEBAPP_PUBLISH_PROFILE`
- **Value**: Paste the **entire content** of the `.PublishSettings` file
- Click **Add secret**

## ✅ Step 3: Verify Secrets

Your secrets should look like this:

```
Repository secrets:
- AZURE_WEBAPP_NAME
- AZURE_WEBAPP_PUBLISH_PROFILE
```

## 🎯 Step 4: Trigger Deployment

### Automatic Deployment (on push to main)

```bash
git add .
git commit -m "Deploy bot to Azure"
git push origin main
```

The workflow will automatically start.

### Manual Deployment

1. Go to **GitHub** → Your repository → **Actions**
2. Select **Deploy to Azure Web App** workflow
3. Click **Run workflow** → **Run workflow**

## 📊 Step 5: Monitor Deployment

1. Go to **Actions** tab in your GitHub repository
2. Click on the running workflow
3. Watch the deployment progress in real-time

You'll see:
- ✅ Checkout code
- ✅ Set up Python
- ✅ Install dependencies
- ✅ Create deployment package
- ✅ Deploy to Azure
- ✅ Deployment summary

## 🔍 Step 6: Verify Deployment

### Check Azure Web App

1. Go to **Azure Portal** → Your **Web App**
2. Navigate to **Deployment Center** → **Logs**
3. Verify deployment succeeded

### Check Logs

1. Go to **App Service** → **Monitoring** → **Log stream**
2. You should see the bot starting up

### Test the Bot

1. Go to **Azure Portal** → Your **Azure Bot** → **Test in Web Chat**
2. Send a test message
3. Verify you get a streaming response

## 🐛 Troubleshooting

### Error: "Resource not found"

**Solution:**
- Verify `AZURE_WEBAPP_NAME` secret is correct
- Check that the Web App exists in Azure

### Error: "Authentication failed"

**Solution:**
- Re-download the publish profile
- Update `AZURE_WEBAPP_PUBLISH_PROFILE` secret
- Make sure you copied the **entire** XML content

### Error: "Deployment package too large"

**Solution:**
- The workflow already excludes common files
- If needed, add more exclusions in `.github/workflows/deploy-to-azure.yml`

### Deployment succeeds but bot doesn't work

**Solution:**
1. Check environment variables are configured in Azure App Service
2. Verify Managed Identity is associated with the Web App
3. Check logs in Azure Portal

## 🔄 Workflow Customization

### Change Deployment Branch

Edit `.github/workflows/deploy-to-azure.yml`:

```yaml
on:
  push:
    branches:
      - production  # Change to your branch
```

### Add Pre-deployment Tests

Uncomment these lines in the workflow:

```yaml
- name: 'Run tests'
  run: |
    pip install pytest
    pytest
```

### Deploy on Pull Request

Add this to the `on:` section:

```yaml
on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main  # Deploy on PRs to main
```

### Add Slack/Teams Notifications

Add a notification step at the end:

```yaml
- name: 'Notify Team'
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

## 📝 Best Practices

### 1. Use Staging Slots

Deploy to a staging slot first:

```yaml
- name: 'Deploy to Staging'
  uses: azure/webapps-deploy@v3
  with:
    app-name: ${{ secrets.AZURE_WEBAPP_NAME }}
    slot-name: staging
    publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
    package: deployment.zip
```

Then swap to production after testing.

### 2. Environment Variables in GitHub

Store non-sensitive config in GitHub:

```yaml
env:
  PYTHON_VERSION: '3.12'
  AZURE_WEBAPP_PACKAGE_PATH: '.'
  LOG_LEVEL: 'INFO'
```

### 3. Version Tagging

Tag releases for better tracking:

```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### 4. Rollback Strategy

Keep previous deployments for quick rollback:
1. Go to **Deployment Center** in Azure Portal
2. Select a previous deployment
3. Click **Redeploy**

## 🔒 Security Notes

### ⚠️ Never commit these to Git:

- ❌ `.PublishSettings` files
- ❌ API keys
- ❌ Passwords
- ❌ Connection strings

### ✅ Always use GitHub Secrets for:

- ✅ Publish profiles
- ✅ API keys
- ✅ Any sensitive data

## 📊 Deployment Checklist

Before first deployment:

- [ ] GitHub secrets configured
  - [ ] `AZURE_WEBAPP_NAME`
  - [ ] `AZURE_WEBAPP_PUBLISH_PROFILE`
- [ ] Environment variables configured in Azure App Service
- [ ] Managed Identity associated with Web App
- [ ] Messaging endpoint configured in Bot Service
- [ ] Workflow file committed to repository

After deployment:

- [ ] Check GitHub Actions workflow completed
- [ ] Verify app is running in Azure Portal
- [ ] Check logs for errors
- [ ] Test bot in Web Chat
- [ ] Verify multitenant validation works

## 🎉 Success!

Once configured, every push to `main` will automatically:
1. Build your bot
2. Create a deployment package
3. Deploy to Azure Web App
4. Your bot will be live in seconds!

## 🔗 Useful Links

- [GitHub Actions Documentation](https://docs.github.com/actions)
- [Azure Web Apps Deploy Action](https://github.com/Azure/webapps-deploy)
- [Azure App Service Deployment](https://learn.microsoft.com/azure/app-service/deploy-github-actions)

---

**Need help?** Check the workflow logs in the Actions tab of your repository.
