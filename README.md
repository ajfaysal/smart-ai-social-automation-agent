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
| `TWEETCLAW_RESEARCH_JSON` | Optional reviewed X/Twitter context exported from TweetClaw before the run. |

Optional model and prompt controls are also supported by the script:

| Variable | Description |
| :--- | :--- |
| `PREMIUM_API_URL` | Override the default language-model endpoint. |
| `PREMIUM_MODEL` | Override the default language-model name. |
| `SYSTEM_PROMPT` | Set the posting style, audience, and safety rules. |
| `USER_PROMPT` | Set the topic or campaign request for the next post. |
| `TWEETCLAW_RESEARCH_FILE` | Read reviewed TweetClaw context from a JSON file path instead of an environment value. |

### Optional TweetClaw Research Context

Use [TweetClaw](https://github.com/Xquik-dev/tweetclaw) when you want OpenClaw to collect reviewed public X/Twitter context before this agent writes a post. It can search tweets, search tweet replies, run user lookup, export followers, monitor tweets, and return tweet IDs, authors, URLs, text, timestamps, and public metrics.

Install TweetClaw in OpenClaw, run the research task, review the returned public records, and paste the final JSON into the `TWEETCLAW_RESEARCH_JSON` GitHub secret. The script treats that content as untrusted background, adds it to `USER_PROMPT`, and tells the model not to follow instructions embedded in tweets, bios, names, or linked content.

```bash
openclaw plugins install @xquik/tweetclaw
```

### 4. Enable GitHub Actions
1. Go to the **Actions** tab in your repository.
2. Click the green button that says **"I understand my workflows, go ahead and enable them"**.
3. Select the **X Automation** workflow from the left sidebar.
4. Click **Run workflow** to test your first automated post instantly!

---
## 📜 License
Distributed under the MIT License. Feel free to use, modify, and distribute.

Xquik is an independent third-party service. Not affiliated with X Corp. "Twitter" and "X" are trademarks of X Corp.
