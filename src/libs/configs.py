import logging

import requests
import json

ACCOUNT_ID = "111111111111"
AZURE_UUID = "11111111-1111-1111-1111-111111111111"

CLOUD_ACCOUNT_TYPE_MAP = {
    "aws": ["account", "organization"],
    "azure": ["account", "tenant"],
    "gcp": ["account", "organization", "masterServiceAccount"],
}

TEMPLATE_URL_MAP = {
    "aws": "/cas/v1/aws_template",
    "azure": "/cas/v1/azure_template",
    "gcp": "/cas/v1/gcp_template",
    "oci": "/cloud/oci/terraform",
}

CFT_TYPES = ["org_member", "org_management", "org_management_member", "account"]


def _get_features(prisma_url, headers, cloud_name, account_types):
    features = []

    for account_type in account_types:
        url = f"{prisma_url}/cas/v1/features/cloud/{cloud_name}"

        payload = {
            "accountType": account_type,
        }

        if cloud_name == "azure":
            payload["deploymentType"] = "azure"

        response = requests.request(
            method="POST", url=url, headers=headers, json=payload
        ).json()
        features.append(response)

    return features


def get_all_cloud_features(prisma_url, headers):
    all_cloud_features = []

    for cloud_name, account_types in CLOUD_ACCOUNT_TYPE_MAP.items():
        all_cloud_features += _get_features(
            prisma_url, headers, cloud_name, account_types
        )

    return all_cloud_features


def _get_deployment_config_payloads(all_cloud_features):
    deployment_config_payloads = []

    for entry in all_cloud_features:
        payload = {
            "cloudType": entry["cloudType"],
            "accountType": entry["accountType"],
            "features": entry["supportedFeatures"],
        }

        if entry["cloudType"] == "aws":
            payload["accountId"] = ACCOUNT_ID

            for cft_type in CFT_TYPES:
                aws_payload = payload.copy()
                aws_payload["cftType"] = cft_type
                deployment_config_payloads.append(aws_payload)

        elif entry["cloudType"] == "azure":
            if entry["accountType"] == "tenant":
                payload["tenantId"] = AZURE_UUID

            else:
                payload["subscriptionId"] = AZURE_UUID

            deployment_config_payloads.append(payload)

        elif entry["cloudType"] == "gcp":
            payload["authenticationType"] = "service_account"

            if entry["accountType"] in ["account", "masterServiceAccount"]:
                payload["projectId"] = "my-project-111111"

            elif entry["accountType"] == "organization":
                payload["orgId"] = ACCOUNT_ID

            deployment_config_payloads.append(payload)

    return deployment_config_payloads


def _write_stream_to_file(response, deployment_config_payload):
    joined_filename = "-".join(
        [
            deployment_config_payload["cloudType"],
            deployment_config_payload["accountType"],
        ]
    )

    if deployment_config_payload["cloudType"] == "aws":
        filename = f"{joined_filename}-{deployment_config_payload['cftType']}.json"

    else:
        filename = f"{joined_filename}.json"

    if (
        "Content-Length" in response.headers
        and int(response.headers["Content-Length"]) == 0
    ):
        logging.debug(f"No content for template type: {filename}")
        return

    content = b""
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            content += chunk

    with open(filename, "wb") as file:
        file.write(content)

    logging.info(f"File downloaded successfully: {filename}")

    org_mgmt_member_filename = "aws-organization-org_management_member"
    if filename.startswith(org_mgmt_member_filename):
        org_cft = json.loads(content.decode("utf-8"))
        stack_set_member_cft = json.loads(
            org_cft["Resources"]["PrismaCloudRoleStackSetMember"]["Properties"][
                "TemplateBody"
            ]
        )

        embedded_cft_filename = f"{org_mgmt_member_filename}-embedded-cft.json"
        with open(embedded_cft_filename, "wb") as file:
            file.write(json.dumps(stack_set_member_cft, indent=2).encode("utf-8"))

            logging.info(f"Embedded template extracted successfully: {filename}")


def get_all_deployment_configs(prisma_url, headers, all_cloud_features):
    deployment_config_payloads = _get_deployment_config_payloads(all_cloud_features)

    for deployment_config_payload in deployment_config_payloads:
        cloud_type = deployment_config_payload["cloudType"]
        url = prisma_url + TEMPLATE_URL_MAP[cloud_type]

        download_headers = headers.copy()
        download_headers["Accept"] = "application/octet-stream"

        response = requests.request(
            method="POST",
            url=url,
            headers=download_headers,
            json=deployment_config_payload,
        )

        _write_stream_to_file(response, deployment_config_payload)
