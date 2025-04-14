### Config `.env`
```
CDP_API_KEY_NAME="test" # Place your CDP API key name here
CDP_API_KEY_PRIVATE_KEY="<CDP_API_KEY_PRIVATE_KEY>" # Place your CDP API key private key here
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

### Setup build and compile environment
```bash
# Create a virtual environment  
python3 -m venv myenv
````
# Install package
```bash
pip install -r requirements.txt
```

### Start telegram bot
```
#!/bin/bash
python telegram_bot.py >> telegram.log 2>&1 &
```