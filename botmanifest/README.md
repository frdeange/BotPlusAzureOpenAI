# Teams Bot Manifest

This directory contains the Microsoft Teams app manifest files for the bot.

## Files

- **manifest.example.json**: Template manifest file with placeholders
- **manifest.json**: Your actual manifest (ignored by git for security)
- **color.png**: Full-color icon (192x192 px)
- **outline.png**: White transparent outline icon (32x32 px)

## Quick Start

### 1. Create Your Manifest

Copy the example file and customize it with your values:

```bash
cp manifest.example.json manifest.json
```

### 2. Update Required Fields

Edit `manifest.json` and replace these placeholders:

| Field | What to Replace | Where to Find |
|-------|----------------|---------------|
| `id` | New GUID | Generate at [guidgen.com](https://www.guidgen.com/) |
| `packageName` | Your package name | e.g., `com.yourcompany.botname` |
| `name.short` | Bot display name | Max 30 characters |
| `name.full` | Full bot name | Max 100 characters |
| `description.*` | Bot descriptions | Short (80 chars) and full (4000 chars) |
| `developer.*` | Your company info | Name, website, privacy, terms URLs |
| `bots[0].botId` | **Managed Identity Client ID** | From Azure Portal → Managed Identity |
| `validDomains[0]` | App Service hostname | e.g., `app-bot-xxx.azurewebsites.net` (no `https://`) |

**⚠️ Critical**: 
- `botId` MUST match your Managed Identity Client ID exactly
- `validDomains` MUST be just the hostname (no protocol or path)

### 3. Create App Package

Package the manifest and icons into a ZIP file:

```bash
cd botmanifest
zip manifest.zip manifest.json color.png outline.png
```

### 4. Upload to Teams

1. Open **Microsoft Teams**
2. Go to **Apps** → **Manage your apps**
3. Click **Upload an app** → **Upload a custom app**
4. Select `manifest.zip`
5. Click **Add**

## Icon Requirements

| File | Size | Format | Description |
|------|------|--------|-------------|
| `color.png` | 192x192 px | PNG with transparency | Full-color app icon |
| `outline.png` | 32x32 px | PNG with transparency | White outline on transparent background |

**Default icons are provided.** Replace them with your own branding.

## Validation

Before uploading, validate your manifest:

- [Teams App Validator](https://dev.teams.microsoft.com/appvalidation.html)
- Or use Teams Toolkit in VS Code

## Security Note

**Never commit `manifest.json` to git!** It contains your actual bot configuration and is automatically ignored via `.gitignore`.

Always use `manifest.example.json` as a template for sharing with others.

## Troubleshooting

### "Invalid app package" error

- Verify ZIP contains exactly 3 files: `manifest.json`, `color.png`, `outline.png`
- Check `botId` is a valid GUID format
- Verify `validDomains` has no `https://` prefix
- Validate JSON syntax

### Bot doesn't appear in Teams

- Verify custom app upload is enabled in Teams Admin Center
- Check bot ID matches your Managed Identity Client ID
- Ensure App Service is running and accessible

## Learn More

See the [SETUP_GUIDE.md](../SETUP_GUIDE.md) in the root directory for complete step-by-step instructions.
