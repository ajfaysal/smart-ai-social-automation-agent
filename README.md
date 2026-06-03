# 🚀 Serverless AI Social Automation Agent

An automated, open-source AI agent powered by GitHub Actions and Playwright to automate trend research, content creation, and media publishing on X (Twitter). It supports custom API integrations so anyone can run their own personal social media manager completely free.

---

## ✨ Features
- **Serverless Automation:** Runs entirely on GitHub Actions cron jobs. No paid hosting or local server required.
- **Dynamic Content Generation:** Leverages advanced AI models via custom API endpoints for high-quality, targeted copywriting.
- **Automated Media Integration:** Automatically generates contextual visual prompts and fetches beautiful graphics via Pollinations AI.
- **Advanced Evasion Engine:** Built-in aggressive JavaScript injection and keyboard emulation to handle modern UI layouts and popup blockages smoothly.

---

## 🛠️ Setup Guide for Public Users

Follow these simple steps to deploy your own personal version of this AI Agent in less than 5 minutes:

### 1. Fork this Repository
Click the **Fork** button at the top right of this page to create a copy of this repository under your own GitHub account.

### 2. Prepare Your API Credentials
You will need two things to power this agent:
1. **AI API Key:** Get an API key from your preferred provider (supporting custom endpoints) to handle content generation.
2. **X Cookies:** Log into X (Twitter) on your desktop browser, use a Cookie Editor extension, and export your cookies in **JSON format**.

### 3. Configure GitHub Secrets
In your forked repository, go to **Settings > Secrets and variables > Actions** and click **New repository secret** to add the following variables:

| Secret Name | Description |
| :--- | :--- |
| `PREMIUM_API_KEY` | Your customized API Key for the language model. |
| `X_COOKIES` | The complete JSON array string of your logged-in X session cookies. |

### 4. Enable GitHub Actions
1. Go to the **Actions** tab in your repository.
2. Click the green button that says **"I understand my workflows, go ahead and enable them"**.
3. Select the **X Automation** workflow from the left sidebar.
4. Click **Run workflow** to test your first automated post instantly!

---
## 📜 License
Distributed under the MIT License. Feel free to use, modify, and distribute.
