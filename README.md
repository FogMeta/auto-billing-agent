# Auto-Billing-Agent

**Auto-Billing-Agent** is an AI-powered invoice automation tool that allows users to interact via natural language to upload, parse, analyze, and process invoices — including payment execution and full data traceability. Powered by LLMs (e.g., LLaMA 3 70B) and integrated with **[Storacha](https://storacha.network/)** for secure data storage, this agent automates the entire billing lifecycle.

It supports:
- Natural language-driven invoice parsing and payment
- Storing original inputs, parsed data, chain of thought, and txhash metadata
- Configurable logging: users can decide whether to store all intermediate steps
- **[Storacha](https://storacha.network/) integration** for data upload, download, and decentralized storage
- Telegram bot interface for convenient communication and usage

---

## 🚀 Features

- ✅ AI-driven semantic understanding of invoice content  
- ✅ Supports structured data extraction and crypto payments  
- ✅ Optionally stores processing steps (chain of thought) for traceability  
- ✅ Fully integrated with **[Storacha](https://storacha.network/)** for secure, decentralized data storage  
- ✅ Telegram Bot interface for real-time interaction and status checking  

---

## 🧹 Installation Steps

### 1. Configure `.env`  
Create a `.env` file in the project root with the following content:

```env
CDP_API_KEY_NAME="test"
CDP_API_KEY_PRIVATE_KEY="<CDP_API_KEY_PRIVATE_KEY>"
PRIVATE_KEY="YOUR_PRIVATE_KEY"
LLM_API_KEY="YOUR_LLM_API_KEY"
LLM_MODEL="meta-llama/Llama-3.3-70B-Instruct"
LLM_BASE_URL="https://inference.nebulablock.com/v1"

TELEGRAM_BOT_TOKEN="<YOUR_TELEGRAM_BOT_TOKEN>"

AUTO_SAVE_THINK=1

STORACHA_SPACE_DID="<YOUR_STORACHA_SPACE_DID>"
STORACHA_AUTH_SECRET="YOUR_STORACHA_AUTH_SECRET"
STORACHA_AUTH_TOKEN="<YOUR_STORACHA_AUTH_TOKEN>"
```

### 2. Set up build environment

```bash
# Create a virtual environment  
python3 -m venv myenv
source myenv/bin/activate

# Install dependencies  
pip install -r requirements.txt
```

### 3. Start the Telegram bot

```bash
#!/bin/bash
python telegram_bot.py >> telegram.log 2>&1 &
```

---

## 📦 Storacha Configuration

To use [Storacha](https://storacha.network/) for data storage, follow these steps:

1. **Create account, space, and keys:**  
   Reference the official guide:  
   👉 https://docs.storacha.network/how-to/http-bridge/

2. **Alternatively, use the web console:**  
   👉 [Storacha Console](https://console.storacha.network/)

3. Paste the generated values into your `.env` file under:
   - `STORACHA_SPACE_DID`
   - `STORACHA_AUTH_SECRET`
   - `STORACHA_AUTH_TOKEN`

---

## 💬 Telegram Bot Interaction

Users can easily interact with the billing agent via Telegram. Just upload an invoice, ask questions, or trigger a payment. The agent will handle:
- Parsing
- Data storage
- Payment status updates

> 📌 *Demo illustration*
