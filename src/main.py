import logging
import os
import sys
import requests
from urllib3.exceptions import InsecureRequestWarning

from libs.configs import get_all_cloud_features, get_all_deployment_configs

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logging.getLogger("urllib3").setLevel(logging.WARNING)
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def get_api_url():
    try:
        prisma_api_url = os.environ["PRISMA_API_URL"]

    except KeyError:
        sys.exit("Please specify the PRISMA_API_URL environment variable.")

    return prisma_api_url


def get_token(prisma_url):
    try:
        prisma_access_key_id = os.environ["PRISMA_ACCESS_KEY_ID"]
        prisma_access_secret_key = os.environ["PRISMA_SECRET_ACCESS_KEY"]
        payload = {
            "username": prisma_access_key_id,
            "password": prisma_access_secret_key,
        }

    except KeyError:
        sys.exit(
            "Please specify the PRISMA_ACCESS_KEY_ID and PRISMA_SECRET_ACCESS_KEY environment variables."
        )

    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json; charset=UTF-8",
    }

    login_url = f"{prisma_url}/login"
    response = requests.request("POST", login_url, headers=headers, json=payload)

    token = response.json()["token"]

    return token


def get_headers(token):
    headers = {"Accept": "application/json; charset=UTF-8", "x-redlock-auth": token}

    return headers


def main():
    prisma_url = get_api_url()
    token = get_token(prisma_url)
    headers = get_headers(token)

    all_cloud_features = get_all_cloud_features(prisma_url, headers)
    get_all_deployment_configs(prisma_url, headers, all_cloud_features)


if __name__ == "__main__":
    main()
