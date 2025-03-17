import os
import asyncio
import logging
import time
import json

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Dict, Optional
from eth_account import Account
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from coinbase_agentkit import (
    AgentKit,
    AgentKitConfig,
    EthAccountWalletProvider,
    EthAccountWalletProviderConfig,
    pyth_action_provider,
    erc20_action_provider,
    wallet_action_provider,
    weth_action_provider,
)
import PyPDF2
from io import BytesIO
from coinbase_agentkit_langchain import get_langchain_tools

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def async_initialize_agent():
    """Initialize the agent asynchronously to avoid blocking FastAPI startup."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, initialize_agent)


def initialize_agent():
    """Initialize the agent with an Ethereum Account Wallet Provider."""
    logger.info("Initializing agent...")

    # Initialize LLM
    llm = ChatOpenAI(model=os.getenv('LLM_MODEL'), base_url=os.getenv('LLM_BASE_URL'), api_key=os.getenv("LLM_API_KEY"))

    # Ensure PRIVATE_KEY is set
    private_key = os.getenv("PRIVATE_KEY")
    assert private_key, "You must set the PRIVATE_KEY environment variable"
    assert private_key.startswith("0x"), "Private key must start with 0x hex prefix"

    # Create Ethereum account from private key
    account = Account.from_key(private_key)

    # Initialize Ethereum Account Wallet Provider
    wallet_provider = EthAccountWalletProvider(
        config=EthAccountWalletProviderConfig(account=account, rpc_url='https://rpc-proxima.swanchain.io',
                                              chain_id="20241133")
    )

    # Initialize AgentKit
    agentkit = AgentKit(
        AgentKitConfig(
            wallet_provider=wallet_provider,
            action_providers=[
                erc20_action_provider(),
                pyth_action_provider(),
                wallet_action_provider(),
                weth_action_provider(),
            ],
        )
    )

    # Get LangChain tools
    tools = get_langchain_tools(agentkit)

    # Store conversation history in memory
    memory = MemorySaver()
    config = {"configurable": {"thread_id": "Ethereum Account Chatbot"}}

    # Create ReAct Agent
    agent_executor = create_react_agent(
        llm,
        tools=tools,
        checkpointer=memory,
        state_modifier=(
            "You are a helpful agent that can interact onchain using an Ethereum Account Wallet. "
            "You have tools to send transactions, query blockchain data, and interact with contracts. "
            "If you encounter a 5XX (internal) error, ask the user to try again later."
        ),
    )

    logger.info("Agent initialized successfully")
    return agent_executor, config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifecycle manager, handling agent initialization and cleanup."""
    logger.info("Starting FastAPI application...")

    # Initialize the agent asynchronously
    app.state.agent_executor, app.state.agent_config = await async_initialize_agent()

    logger.info("Agent is ready for requests.")
    yield  # Run FastAPI application

    # Cleanup resources on shutdown
    logger.info("Shutting down agent and releasing resources...")
    if hasattr(app.state, "agent_executor"):
        del app.state.agent_executor
    if hasattr(app.state, "agent_config"):
        del app.state.agent_config
    logger.info("Agent resources have been released.")


def fetch_billing_info():
    """Fetch billing info from the given URL."""
    url = "http://localhost:8020/bill_monitor"

    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors

        # Parse the JSON data
        data = response.json()

        # Check if status is 'success'
        if data.get("status") == "success":
            print("Billing Information retrieved successfully:")
            result = json.dumps(data, indent=4)
            print(result)
            bill_url = data.get("data", {}).get("bill_url")
            if bill_url:
                content = download_and_parse_pdf(bill_url)
                print('content: ', content)
                prompt = """
                        Extract the payment information from the invoice and execute the payment transfer function. Please perform the payment operation based on the following details:
                        {invoice_info}

                        ### Task Requirements:
                        1. **Extract and validate the payment information**:  
                           - Ensure the **Total Amount Due** is correct and matches the itemized total.
                           - Validate the **Client Wallet Address**, **Token Contract Address**, and **Payment Contract Address** to ensure they are valid for the payment transfer.

                        2. **Initiate the payment transfer**:
                           - Use the **Client Wallet Address** and **Payment Contract Address** to initiate the transfer of 1 SWAN.
                           - Ensure the transfer is executed with the correct **Token Contract Address**.

                        3. **Execute the transfer function** to pay **1 SWAN**:
                           - Call the appropriate function to transfer the payment from the client wallet to the payment contract.

                        4. **Verify the payment**:
                           - After the transaction is completed, confirm that the payment has been processed and the 1 SWAN has been successfully transferred.
                        """.format(invoice_info=content)
                run_chat_mode(prompt)
            else:
                print("Bill URL not found in the response.")
        else:
            print(f"Error: {data.get('message')}")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")


def start_periodic_fetch():
    """Start fetching billing info every 10 seconds."""
    while True:
        fetch_billing_info()
        time.sleep(3600)  # Wait for 10 seconds before the next fetch


def download_and_parse_pdf(url):
    """
    Download and parse PDF file from given URL
    
    Args:
        url (str): URL of the PDF file
    
    Returns:
        str: Text content of the PDF file
    """
    try:
        # Download PDF file
        response = requests.get(url)
        response.raise_for_status()  # Check if download was successful

        # Create a file object in memory using BytesIO
        pdf_file = BytesIO(response.content)

        # Create PDF reader object
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        # Extract text from all pages
        text_content = []
        for page in pdf_reader.pages:
            text_content.append(page.extract_text())

        return "\n".join(text_content)

    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF file: {e}")
        return None
    except Exception as e:
        print(f"Error parsing PDF file: {e}")
        return None


def run_chat_mode(input_str: str):
    agent_executor, config = initialize_agent()
    try:
        # Run agent with the user's input in chat mode
        for chunk in agent_executor.stream(
                {"messages": [HumanMessage(content=input_str)]}, config
        ):
            print("chunk:", chunk)
            if "agent" in chunk:
                print(chunk["agent"]["messages"][0].content)
            elif "tools" in chunk:
                print(chunk["tools"]["messages"][0].content)
            print("-------------------")

    except Exception as e:
        print(f"Error parsing PDF file: {e}")


app = FastAPI(title="Blockchain Agent API", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str
    mode: Optional[str] = "chat"  # Options: "chat" or "auto"


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> Dict[str, str]:
    """API endpoint to interact with the agent."""
    try:
        agent_executor = app.state.agent_executor
        agent_config = app.state.agent_config
        print("input: ", request.message, "agent_config:", agent_config)
        response_chunks = []
        for chunk in agent_executor.stream(
                {"messages": [HumanMessage(content=request.message)]},
                agent_config
        ):
            print("chunk:", chunk)
            if "agent" in chunk:
                response_chunks.append(chunk["agent"]["messages"][0].content)
            elif "tools" in chunk:
                response_chunks.append(chunk["tools"]["messages"][0].content)

        return {"response": "\n".join(response_chunks)}
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


if __name__ == "__main__":
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    start_periodic_fetch()
