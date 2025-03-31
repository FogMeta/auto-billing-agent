import subprocess
import requests
from typing import Dict, List
from dotenv import load_dotenv

GATE_WAY_URL=".ipfs.w3s.link"


def get_file_url(cid: str) -> str:
    return "https://"+cid+GATE_WAY_URL


class StorachaClient:
    def __init__(self, auth_secret: str, auth_token: str, base_url: str = "https://up.storacha.network/bridge"):
        self.auth_secret = auth_secret
        self.auth_token = auth_token
        self.base_url = base_url
        self.headers = {
            "X-Auth-Secret": auth_secret,
            "Authorization": auth_token
        }

    def _make_request(self, tasks: List) -> Dict:
        payload = {"tasks": tasks}
        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def list_uploads(self, space_did: str) -> Dict:
        tasks = [["upload/list", space_did, {}]]
        return self._make_request(tasks)

    def store_file(self, space_did: str, file_path: str) -> Dict:
        car_path = f"{file_path}.car"
        subprocess.run(["ipfs-car", "pack", file_path, "-o", car_path], check=True)

        result = subprocess.run(
            ["ipfs-car", "hash", car_path],
            capture_output=True,
            text=True,
            check=True
        )
        car_hash = result.stdout.strip()

        car_size = subprocess.run(
            ["wc", "-c", car_path],
            capture_output=True,
            text=True,
            check=True
        ).stdout.split()[0]

        tasks = [[
            "store/add",
            space_did,
            {
                "link": {"/": car_hash},
                "size": int(car_size)
            }
        ]]

        response = self._make_request(tasks)

        # Check if we need to perform the PUT request
        result = response[0]['p']['out']['ok']
        if result['status'] == 'upload':
            # Read the CAR file
            with open(car_path, 'rb') as f:
                car_data = f.read()

            # Perform PUT request
            put_response = requests.put(
                result['url'],
                data=car_data,
                headers=result['headers']
            )
            put_response.raise_for_status()
        return response

    def upload_file(self, space_did: str, file_path: str) -> Dict:
        car_path = f"{file_path}.car"
        # Get the root CID
        pack_result = subprocess.run(
            ["ipfs-car", "pack", file_path, "-o", car_path],
            capture_output=True,
            text=True,
            check=True
        )
        root_cid = pack_result.stdout.strip()

        # Get the CAR hash (shard CID)
        result = subprocess.run(
            ["ipfs-car", "hash", car_path],
            capture_output=True,
            text=True,
            check=True
        )
        car_hash = result.stdout.strip()

        tasks = [[
            "upload/add",
            space_did,
            {
                "root": {"/": root_cid},
                "shards": [
                    {"/": car_hash}
                ]
            }
        ]]
        response = self._make_request(tasks)
        upload_result = response[0]['p']['out']['ok']
        return upload_result['root']['/']


    @staticmethod
    def generate_auth_tokens(space_did: str, capabilities: List[str], expiration_hours: int = 24) -> Dict[str, str]:
        # Calculate expiration timestamp in Python
        from datetime import datetime, timedelta
        expiration = int((datetime.now() + timedelta(hours=expiration_hours)).timestamp())

        cmd = [
            "w3", "bridge", "generate-tokens",
            space_did
        ]

        for cap in capabilities:
            cmd.extend(["--can", cap])

        cmd.extend([
            "--expiration",
            str(expiration)
        ])

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        output_lines = result.stdout.split('\n')
        auth_secret = output_lines[1].split(': ')[1]
        auth_token = output_lines[3].split(': ')[1]

        return {
            "auth_secret": auth_secret,
            "auth_token": auth_token
        }


if __name__ == '__main__':
    load_dotenv()

    space_did = "did:key:z6MksW41jyzcneawTbquk28jUULz3DmBCzYhauuCb6mLgG8o"
    capabilities = ["store/add", "upload/add", "upload/list"]
    tokens = StorachaClient.generate_auth_tokens(space_did, capabilities)

    client = StorachaClient(
        auth_secret=tokens["auth_secret"],
        auth_token=tokens["auth_token"]
    )

    uploads = client.list_uploads(space_did)
    print("Uploads:", uploads)

    result = client.store_file(space_did, "hello.txt")
    print("Store result:", result)

    upload_result = client.upload_file(space_did, "hello.txt")
    print("upload result:", upload_result)

    uploads = client.list_uploads(space_did)
    print("Uploads:", uploads)