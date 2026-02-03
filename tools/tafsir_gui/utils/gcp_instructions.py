from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class GCPInstructions:
    console_block: str
    cli_block: str
    urls: Dict[str, str]
    steps: List[str]
    cli_steps: List[str]


def _slugify(name: str) -> str:
    return urllib.parse.quote(name.lower().replace(" ", "-"))


def generate_instructions(
    project_name: str,
    billing_country: str | None = None,
    org_folder: str | None = None,
) -> GCPInstructions:
    slug = _slugify(project_name or "my-project")
    base_project_param = f"project={slug}"

    urls = {
        "console_home": "https://console.cloud.google.com",
        "project_selector": "https://console.cloud.google.com/projectselector2/home?walkthrough_id=projectpicker&pli=1",
        "api_library": f"https://console.cloud.google.com/apis/library?{base_project_param}",
        "credentials": f"https://console.cloud.google.com/apis/credentials?{base_project_param}",
        "quotas": f"https://console.cloud.google.com/iam-admin/quotas?{base_project_param}",
        "billing": f"https://console.cloud.google.com/billing?{base_project_param}",
        "gemini_search": "https://console.cloud.google.com/apis/library/generative-language.googleapis.com",
    }

    steps = [
        "Open Project Selector and create/select your project.",
        "Go to API Library, search “Generative Language API”, click Enable.",
        "Open Credentials page, click “Create credentials” -> “API key”.",
        "Copy the new API key and paste it into the app, then press Test key.",
        "Check Quotas page if you see rate-limit or quota errors.",
        "If prompted about billing, open Billing page and attach a billing account.",
    ]

    cli_steps = [
        "Ensure gcloud is installed and authenticated: `gcloud auth login`.",
        f"Set project (creates if missing): `gcloud projects create {slug}` then `gcloud config set project {slug}`.",
        "Enable API: `gcloud services enable generative-language.googleapis.com`.",
        "Create API key: `gcloud services api-keys create --display-name=\"Gemini Key\"`.",
        "List keys (to copy): `gcloud services api-keys list`.",
        "Test key in the app using the Test key button.",
    ]
    if billing_country:
        cli_steps.insert(
            2,
            "If billing required, run: `gcloud beta billing projects link "
            f"{slug} --billing-account=YOUR_ACCOUNT_ID` (replace with your billing account).",
        )

    console_block = "\n".join(
        [
            "Console-first setup:",
            f"- Project selector: {urls['project_selector']}",
            f"- API library (Generative Language): {urls['gemini_search']}",
            f"- Credentials page: {urls['credentials']}",
            f"- Quotas: {urls['quotas']}",
            f"- Billing: {urls['billing']}",
            "",
            "Click path:",
            "1) Open Project selector, create/select project",
            "2) API Library -> Generative Language API -> Enable",
            "3) APIs & Services -> Credentials -> Create credentials -> API key",
            "4) Copy key to the app -> Test key",
            "5) If rate-limited, check Quotas; if billing required, attach billing account",
        ]
    )

    cli_block = "\n".join(cli_steps)

    return GCPInstructions(
        console_block=console_block,
        cli_block=cli_block,
        urls=urls,
        steps=steps,
        cli_steps=cli_steps,
    )


__all__ = ["generate_instructions", "GCPInstructions"]
