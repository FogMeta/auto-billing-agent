import os
from typing import Dict, Any
import json
from langchain_openai import ChatOpenAI
from bill_action_provider import BillActionProvider
from dotenv import load_dotenv
load_dotenv()


def create_bill_processor():
    bill_provider = BillActionProvider()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "download_pdf",
                "description": "Download a PDF file from the provided URL",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pdf_url": {
                            "type": "string",
                            "description": "URL of the PDF file to download"
                        }
                    },
                    "required": ["pdf_url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "process_bill_transfer",
                "description": "Execute an ERC20 token transfer based on invoice analysis",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "buyer_address": {
                            "type": "string",
                            "description": "Buyer's wallet address"
                        },
                        "seller_address": {
                            "type": "string",
                            "description": "Seller's wallet address"
                        },
                        "token_contract": {
                            "type": "string",
                            "description": "Token contract address"
                        },
                        "amount": {
                            "type": "number",
                            "description": "Transfer amount"
                        }
                    },
                    "required": ["buyer_address", "seller_address", "token_contract", "amount"]
                }
            }
        }
    ]

    llm = ChatOpenAI(
        model=os.getenv('LLM_MODEL'), 
        base_url=os.getenv('LLM_BASE_URL'), 
        api_key=os.getenv("LLM_API_KEY"),
        temperature=0
    )

    def process_invoice(pdf_url: str) -> Dict[str, Any]:
        try:
            # Step 1: Download PDF through LLM
            download_response = llm.invoke(
                [
                    {
                        "role": "system",
                        "content": "You are a professional document processor assistant, responsible for downloading file"
                    },
                    {
                        "role": "user",
                        "content": f"Please download the PDF file from this URL: {pdf_url}"
                    }
                ],
                tools=tools
            )
            print("download_response： ", download_response)
            if not download_response.tool_calls:
                return {"status": "error", "message": "Failed to download PDF: No tool calls returned"}

            try:
                pdf_content = bill_provider.download_pdf(download_response.tool_calls[0]["args"])
            except Exception as e:
                return {"status": "error", "message": f"Failed to download PDF: {str(e)}"}
            
            if not pdf_content:
                return {"status": "error", "message": "PDF content is empty"}

            # Step 2: Use LLM to analyze content and execute transfer
            transfer_response = llm.invoke(
                [
                    {
                        "role": "system",
                        "content": "You are a professional invoice analysis assistant. Analyze the invoice content "
                                   "and process the payment."
                    },
                    {
                        "role": "user",
                        "content": f"""Please analyze this invoice content:{pdf_content}.  
                        Please do not use cached data."""
                    }
                ],
                tools=tools
            )
            
            if not transfer_response.tool_calls:
                return {"status": "error", "message": "Failed to analyze invoice: No tool calls returned"}

            try:
                print("transfer_response: ", transfer_response)
                function_args = transfer_response.tool_calls[0]["args"]
                print("function_args: ", function_args)
                result = bill_provider.process_bill_transfer(function_args)
                print("result: ", result)
                return {"status": "success", "result": result, "invoice_data": function_args}
            except json.JSONDecodeError:
                return {"status": "error", "message": "Failed to parse transfer parameters"}
            except Exception as e:
                return {"status": "error", "message": f"Failed to execute transfer: {str(e)}"}

        except Exception as e:
            return {"status": "error", "message": f"Unexpected error: {str(e)}"}

    return process_invoice


def execute_bill_workflow(pdf_url: str) -> Dict[str, Any]:
    processor = create_bill_processor()
    return processor(pdf_url)


if __name__ == "__main__":
    result = execute_bill_workflow("https://42f6d9f62851.acl.swanipfs.com/ipfs/QmRdBmdaiPFef8jfytCocCEVP6WVjv8ESbdBEStzFL548N")
    print(result)