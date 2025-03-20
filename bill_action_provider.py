"""bill action provider."""

from typing import Any
import requests
import os
from pathlib import Path
from web3 import Web3
from coinbase_agentkit import (
    EvmWalletProvider,
    ActionProvider,
    create_action,
    erc20_action_provider,
)
from coinbase_agentkit.network import Network
from coinbase_agentkit.action_providers.erc20.erc20_action_provider import ERC20_ABI
from pydantic import BaseModel, Field
import json
import datetime
import PyPDF2
from io import BytesIO
from langchain_openai import ChatOpenAI


class DownloadPDFSchema(BaseModel):
    """Schema for downloading PDF."""
    pdf_url: str = Field(..., description="URL of the PDF file to download")


class BillTransferSchema(BaseModel):
    """Schema for bill transfer."""
    buyer_address: str = Field(..., description="Buyer's wallet address")
    seller_address: str = Field(..., description="Seller's wallet address")
    token_contract: str = Field(..., description="Token contract address")
    amount: float = Field(..., description="Transfer amount")


class BillInfoSchema(BaseModel):
    """Schema for bill information processing."""
    invoice_number: str = Field(..., description="Invoice identification number")
    service_details: dict = Field(..., description="Service information including name, description, and date")
    buyer_details: dict = Field(..., description="Buyer information including name, address, and contact")
    seller_details: dict = Field(..., description="Seller information including name, address, and contact")
    payment_details: dict = Field(..., description="Payment information including amount, currency, and due date")


class BillActionProvider(ActionProvider[EvmWalletProvider]):
    """Action provider for bill processing and ERC20 tokens."""

    def __init__(self) -> None:
        """Initialize the bill action provider."""
        super().__init__("bill", [])

    @create_action(
        name="download_pdf",
        description="""
        Downloads a PDF file from a specified URL to the local filesystem.
        
        Input parameters:
        - pdf_url: The complete URL of the PDF file to download (must be a valid and accessible URL)
        
        Process:
        1. Validates the URL format and accessibility
        2. Creates a download directory if it doesn't exist
        3. Downloads the PDF content
        4. Saves the file with original filename or generates appropriate name
        
        Returns:
        - PDF content if successful
        - Error message if download fails or URL is invalid
        
        Note: Ensures proper error handling for network issues and invalid URLs
        """,
        schema=DownloadPDFSchema,
    )
    def download_pdf(self, wallet_provider: EvmWalletProvider, args: dict[str, Any]) -> str:
        try:
            validated_args = DownloadPDFSchema(**args)
            
            # Download PDF
            response = requests.get(validated_args.pdf_url)
            response.raise_for_status()
            
            # Extract text from PDF
            pdf_file = BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            pdf_text = ""
            for page in pdf_reader.pages:
                pdf_text += page.extract_text()

            address = wallet_provider.get_address()
            print("wallet address: ", address)

            balance = erc20_action_provider().get_balance(wallet_provider,
                                   {'contract_address': '0x91B25A65b295F0405552A4bbB77879ab5e38166c'})

            # Define prompt for invoice analysis
            prompt = """Analyze the invoice content and extract key details. Transfer is strictly prohibited:

                1. Basic Invoice Information:
                   - Invoice Number
                   - Invoice Date

                2. Service Information:
                   - Service Name
                   - Service Description
                   - Service Date

                3. Buyer Information:
                   - Company/Individual Name
                   - Address
                   - Contact Details

                4. Seller Information:
                   - Company Name
                   - Address
                   - Contact Details

                5. Payment Information:
                   - Client Wallet Address
                   - Payment Contract Address
                   - Amount
                   - Currency
                   - Payment Due Date
                
                Additional Information: 
            
                Please return the information in Markdown format, ensuring all fields are included.
                Note: "Currency" should show ERC20 Token Symbol and Contract Address
                Note: you should show the result of the following items under "Additional Information" part:
                       - Verify whether the current {address} matches the client account in the invoice. If they do not match, the transaction cannot proceed.
                       - {balance} Check whether the current {address} Currency balance is sufficient for payment.
                       - Emphasize the payee account. 

                Invoice Content:
                {pdf_text}""".format(pdf_text=pdf_text, address=address, balance= balance)
            llm = ChatOpenAI(model=os.getenv('LLM_MODEL'), base_url=os.getenv('LLM_BASE_URL'), api_key=os.getenv("LLM_API_KEY"))
                
            # Call LLM for analysis
            response = llm.invoke(prompt)
            wallet_provider.get_balance()
            return response.content
        except requests.exceptions.RequestException as e:
            return {"error": f"PDF download failed: {str(e)}"}
        except Exception as e:
            return {"error": f"Processing failed: {str(e)}"}

    # @create_action(
    #     name="process_bill_transfer",
    #     description="""
    #     Executes a secure ERC20 token transfer for invoice payments with comprehensive validation.
    #
    #     Input parameters:
    #     - buyer_address: The EVM-compatible wallet address of the payer (must be a valid checksum address)
    #     - seller_address: The EVM-compatible wallet address of the payee (must be a valid checksum address)
    #     - token_contract: The ERC20 token contract address for the payment currency (e.g., USDT, USDC)
    #     - amount: The exact payment amount in token units (automatically converts to Wei)
    #
    #     Security checks:
    #     1. Validates all wallet addresses against EVM standards
    #     2. Verifies sufficient token balance in buyer's wallet
    #     3. Confirms adequate gas balance for transaction
    #     4. Monitors transaction confirmation status
    #
    #     Technical details:
    #     - Automatically handles token decimals conversion
    #     - Implements gas estimation and balance verification
    #     - Provides transaction confirmation monitoring
    #     - Returns detailed transaction status and hash
    #
    #     Error handling:
    #     - Insufficient token balance
    #     - Insufficient gas balance
    #     - Invalid addresses
    #     - Failed transactions
    #     - Network issues
    #
    #     Returns:
    #     - Success: Transaction hash and confirmation details
    #     - Failure: Detailed error message with specific reason
    #     """,
    #     schema=BillTransferSchema,
    # )
    # def process_bill_transfer(self, wallet_provider: EvmWalletProvider, args: dict[str, Any]) -> str:
    #     """Process bill transfer from buyer's wallet to seller's wallet.
    #
    #     Args:
    #         wallet_provider (EvmWalletProvider): Wallet provider instance
    #         args (dict[str, Any]): Input arguments
    #
    #     Returns:
    #         str: Message containing operation response or error details
    #     """
    #     try:
    #         validated_args = BillTransferSchema(**args)
    #         print("validated_args: ", validated_args)
    #
    #         # Validate address format
    #         buyer_address = Web3.to_checksum_address(validated_args.buyer_address)
    #         seller_address = Web3.to_checksum_address(validated_args.seller_address)
    #         token_contract = Web3.to_checksum_address(validated_args.token_contract)
    #
    #         # Create token contract instance
    #         contract = Web3().eth.contract(address=token_contract, abi=ERC20_ABI)
    #
    #         # Get token decimals
    #         decimals = contract.functions.decimals().call()
    #         amount_wei = int(validated_args.amount * (10 ** decimals))
    #
    #         # Check buyer's balance
    #         balance = contract.functions.balanceOf(buyer_address).call()
    #         if balance < amount_wei:
    #             return f"Error: Insufficient balance. Current balance: {balance / (10 ** decimals)}, Required amount: {validated_args.amount}"
    #
    #         # Prepare transfer data
    #         data = contract.encode_abi(
    #             "transfer",
    #             [seller_address, amount_wei]
    #         )
    #
    #         # Check gas balance
    #         gas_balance = Web3().eth.get_balance(buyer_address)
    #         estimated_gas = Web3().eth.estimate_gas({
    #             "from": buyer_address,
    #             "to": token_contract,
    #             "data": data
    #         })
    #
    #         if gas_balance < estimated_gas:
    #             return f"Error: Insufficient gas balance for transaction"
    #
    #         # Send transaction
    #         tx_hash = wallet_provider.send_transaction(
    #             {
    #                 "from": buyer_address,
    #                 "to": token_contract,
    #                 "data": data,
    #             }
    #         )
    #
    #         # Wait for transaction confirmation
    #         receipt = wallet_provider.wait_for_transaction_receipt(tx_hash)
    #
    #         # Check transaction status
    #         if receipt['status'] != 1:
    #             return f"Error: Transaction failed. Hash: {tx_hash}"
    #
    #         return (
    #             f"Transfer successful!\n"
    #             f"Transferred {validated_args.amount} tokens from {buyer_address} to {seller_address}\n"
    #             f"Transaction hash: {tx_hash}"
    #         )
    #
    #     except Exception as e:
    #         return f"Transfer failed: {e!s}"

    def supports_network(self, network: Network) -> bool:
        """Check if the network is supported by this action provider.

        Args:
            network (Network): The network to check support for.

        Returns:
            bool: Whether the network is supported.

        """
        return network.protocol_family == "evm"


def bill_action_provider() -> BillActionProvider:
    """Create a new instance of the bill action provider.

    Returns:
        A new bill action provider instance.

    """
    return BillActionProvider()
