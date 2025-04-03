from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from coinbase_agentkit import ActionProvider, create_action, EvmWalletProvider
from coinbase_agentkit.network import Network
from storacha_client import StorachaClient, get_file_url
import json
import os
from datetime import datetime


class SaveAnalysisSchema(BaseModel):
    """Schema for saving analysis content."""
    content: str = Field(..., description="Analysis content to be saved")
    title: str = Field(..., description="Title of the analysis")


class StorachaActionProvider(ActionProvider[EvmWalletProvider]):
    """Action provider for bill processing and ERC20 tokens."""

    def __init__(self) -> None:
        """Initialize the bill action provider."""
        super().__init__("storacha", [])
        self.space_did = os.getenv("STORACHA_SPACE_DID")
        self.auth_secret = os.getenv("STORACHA_AUTH_SECRET")
        self.auth_token = os.getenv("STORACHA_AUTH_TOKEN")
        self.storacha_client = StorachaClient(
            auth_secret=self.auth_secret,
            auth_token=self.auth_token
        )

    @create_action(
        name="save_analysis",
        description="""
            Saves the analysis result to Storacha storage and returns a download link.
    
            Input parameters:
            - content: The analysis content to be saved
            - title: Title for the analysis file
    
            Returns:
            - Download URL if successful
            - Error message if save fails
            """,
        schema=SaveAnalysisSchema,
    )
    def save_analysis(self, args: dict[str, Any]) -> str:
        try:
            validated_args = SaveAnalysisSchema(**args)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{validated_args.title}_{timestamp}.txt"

            # Save content to temporary file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(validated_args.content)

            try:
                # Upload to Storacha
                self.storacha_client.store_file(self.space_did, filename)
                cid = self.storacha_client.upload_file(self.space_did, filename)
                # Generate download URL
                download_url = get_file_url(cid)
                return f"Analysis saved successfully. Access it here: {download_url}"
            finally:
                # Cleanup temporary file
                if os.path.exists(filename):
                    os.remove(filename)

        except Exception as e:
            return f"Failed to save analysis: {str(e)}"

    def supports_network(self, network: Network) -> bool:
        """Check if the network is supported by this action provider.

        Args:
            network (Network): The network to check support for.

        Returns:
            bool: Whether the network is supported.

        """
        return network.protocol_family == "evm"


def storacha_action_provider() -> StorachaActionProvider:
    """Create a new instance of the bill action provider."""
    return StorachaActionProvider()