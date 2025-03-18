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
)
from coinbase_agentkit.network import Network
from coinbase_agentkit.action_providers.erc20.erc20_action_provider import ERC20_ABI
from pydantic import BaseModel, Field
import openai  # Add OpenAI integration

class DownloadPDFSchema(BaseModel):
    """Schema for downloading PDF."""
    pdf_url: str = Field(..., description="URL of the PDF file to download")


class BillTransferSchema(BaseModel):
    """Schema for bill transfer."""
    buyer_address: str = Field(..., description="Buyer's wallet address")
    seller_address: str = Field(..., description="Seller's wallet address")
    token_contract: str = Field(..., description="Token contract address")
    amount: float = Field(..., description="Transfer amount")


class BillActionProvider(ActionProvider[EvmWalletProvider]):
    """Action provider for bill processing and ERC20 tokens."""

    def __init__(self) -> None:
        """Initialize the bill action provider."""
        super().__init__("bill", [])
        # Initialize OpenAI client
        self.openai_client = openai.OpenAI()

    @create_action(
        name="download_pdf",
        description="""
        This tool will download a PDF file from the provided URL and save it locally.
        
        It takes the following inputs:
        - pdf_url: The URL of the PDF file to download
        """,
        schema=DownloadPDFSchema,
    )
    def download_pdf(self, args: dict[str, Any]) -> str:
        try:
            validated_args = DownloadPDFSchema(**args)

            current_dir = Path(__file__).parent
            download_dir = current_dir / "download"
            download_dir.mkdir(parents=True, exist_ok=True)
            
            filename = os.path.basename(validated_args.pdf_url)
            if not filename.endswith('.pdf'):
                filename = f"{filename}.pdf"
            
            save_path = download_dir / filename

            # Download the PDF
            response = requests.get(validated_args.pdf_url)
            response.raise_for_status()

            with open(save_path, 'wb') as f:
                f.write(response.content)

            return f"Successfully downloaded PDF to {save_path}"
        except Exception as e:
            return f"Error downloading PDF: {e!s}"

    @create_action(
        name="process_bill_transfer",
        description="""
        Execute an ERC20 token transfer based on invoice analysis results. This function handles the payment process for bills and invoices.
        
        Input parameters:
        - buyer_address: The EVM wallet address of the invoice payer/buyer
        - seller_address: The EVM wallet address of the invoice issuer/seller
        - token_contract: The ERC20 token contract address for payment (e.g., USDT, USDC)
        - amount: The payment amount in token units (e.g., 100 USDT, not Wei)
        
        The function will:
        1. Validate all wallet addresses
        2. Check token balance and gas fees
        3. Execute the token transfer
        4. Wait for transaction confirmation
        
        Important notes:
        - All addresses must be valid EVM addresses
        - Amount is automatically converted to the correct token decimals
        - Transaction will fail if buyer has insufficient balance
        - Returns transaction details or error message
        
        Example usage:
        For an invoice of 100 USDT:
        {
            "buyer_address": "0x123...",
            "seller_address": "0x456...",
            "token_contract": "0x789...",
            "amount": 100.0
        }
        """,
        schema=BillTransferSchema,
    )
    def process_bill_transfer(self, wallet_provider: EvmWalletProvider, args: dict[str, Any]) -> str:
        """Process bill transfer from buyer's wallet to seller's wallet.

        Args:
            wallet_provider (EvmWalletProvider): Wallet provider instance
            args (dict[str, Any]): Input arguments

        Returns:
            str: Message containing operation response or error details
        """
        try:
            validated_args = BillTransferSchema(**args)
            
            # Validate address format
            buyer_address = Web3.to_checksum_address(validated_args.buyer_address)
            seller_address = Web3.to_checksum_address(validated_args.seller_address)
            token_contract = Web3.to_checksum_address(validated_args.token_contract)
            
            # Create token contract instance
            contract = Web3().eth.contract(address=token_contract, abi=ERC20_ABI)
            
            # Get token decimals
            decimals = contract.functions.decimals().call()
            amount_wei = int(validated_args.amount * (10 ** decimals))
            
            # Check buyer's balance
            balance = contract.functions.balanceOf(buyer_address).call()
            if balance < amount_wei:
                return f"Error: Insufficient balance. Current balance: {balance / (10 ** decimals)}, Required amount: {validated_args.amount}"
            
            # Prepare transfer data
            data = contract.encode_abi(
                "transfer",
                [seller_address, amount_wei]
            )
            
            # Check gas balance
            gas_balance = Web3().eth.get_balance(buyer_address)
            estimated_gas = Web3().eth.estimate_gas({
                "from": buyer_address,
                "to": token_contract,
                "data": data
            })
            
            if gas_balance < estimated_gas:
                return f"Error: Insufficient gas balance for transaction"
                
            # Send transaction
            tx_hash = wallet_provider.send_transaction(
                {
                    "from": buyer_address,
                    "to": token_contract,
                    "data": data,
                }
            )
            
            # Wait for transaction confirmation
            receipt = wallet_provider.wait_for_transaction_receipt(tx_hash)
            
            # Check transaction status
            if receipt['status'] != 1:
                return f"Error: Transaction failed. Hash: {tx_hash}"
            
            return (
                f"Transfer successful!\n"
                f"Transferred {validated_args.amount} tokens from {buyer_address} to {seller_address}\n"
                f"Transaction hash: {tx_hash}"
            )
            
        except Exception as e:
            return f"Transfer failed: {e!s}"

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
