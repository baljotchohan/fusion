# connectors/github_scanner.py
"""
Real GitHub API connector for repository security scanning.

Pulls live data from GitHub:
  - secret scanning alerts
  - Dependabot vulnerability alerts (package, severity, CVE)
  - dependency manifests (package.json, requirements.txt, Gemfile, go.mod)

Requires GITHUB_TOKEN with `security_events` scope for alert endpoints;
without it, scanning degrades gracefully to public-data analysis only.
"""
import base64
import json
import logging
import os
import re
from typing import List, Dict, Optional

import httpx

logger = logging.getLogger("fusion.connectors.github")

MANIFEST_FILES = [
    ("package.json", "javascript"),
    ("requirements.txt", "python"),
    ("Gemfile", "ruby"),
    ("go.mod", "golang"),
]


def parse_repo_url(repo_url: str) -> tuple:
    """Accepts 'owner/repo' or a full https://github.com/owner/repo URL."""
    cleaned = repo_url.strip().rstrip("/")
    cleaned = re.sub(r"^https?://github\.com/", "", cleaned)
    cleaned = re.sub(r"\.git$", "", cleaned)
    parts = cleaned.split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse GitHub repo from '{repo_url}'")
    return parts[0], parts[1]


class GitHubScanner:
    """Real GitHub API connector used by the Recon and Detection agents."""

    def __init__(self, github_token: Optional[str] = None):
        self.token = github_token or os.getenv("GITHUB_TOKEN", "")
        self.api_base = "https://api.github.com"

    def _headers(self) -> dict:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def scan_repo(self, repo_owner: str, repo_name: str) -> Dict:
        """Scan a real GitHub repo for security issues."""
        findings = {
            "repo": f"{repo_owner}/{repo_name}",
            "exposed_secrets": [],
            "outdated_deps": [],
            "dependabot_alerts": [],
            "repo_metadata": {},
            "errors": [],
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            findings["repo_metadata"] = await self._get_repo_metadata(
                client, repo_owner, repo_name, findings
            )
            findings["exposed_secrets"] = await self._get_secret_scanning_alerts(
                client, repo_owner, repo_name, findings
            )
            findings["outdated_deps"] = await self._analyze_dependencies(
                client, repo_owner, repo_name, findings
            )
            findings["dependabot_alerts"] = await self._get_dependabot_alerts(
                client, repo_owner, repo_name, findings
            )

        findings["summary"] = self._summarize(findings)
        return findings

    async def _get_repo_metadata(self, client, owner, repo, findings) -> Dict:
        try:
            resp = await client.get(
                f"{self.api_base}/repos/{owner}/{repo}", headers=self._headers()
            )
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "default_branch": data.get("default_branch"),
                    "visibility": data.get("visibility"),
                    "open_issues": data.get("open_issues_count"),
                    "pushed_at": data.get("pushed_at"),
                }
            findings["errors"].append(f"repo metadata: HTTP {resp.status_code}")
        except Exception as e:
            findings["errors"].append(f"repo metadata: {e}")
        return {}

    async def _get_secret_scanning_alerts(self, client, owner, repo, findings) -> List[Dict]:
        """Fetch GitHub secret scanning alerts (needs security_events scope)."""
        try:
            resp = await client.get(
                f"{self.api_base}/repos/{owner}/{repo}/secret-scanning/alerts",
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return [
                    {
                        "secret_type": a.get("secret_type"),
                        "created_at": a.get("created_at"),
                        "state": a.get("state"),
                    }
                    for a in resp.json()
                ]
            findings["errors"].append(f"secret scanning: HTTP {resp.status_code}")
        except Exception as e:
            findings["errors"].append(f"secret scanning: {e}")
        return []

    async def _analyze_dependencies(self, client, owner, repo, findings) -> List[Dict]:
        """Pull dependency manifests so Threat Intel can cross-reference CVEs."""
        manifests = []
        for filename, language in MANIFEST_FILES:
            try:
                resp = await client.get(
                    f"{self.api_base}/repos/{owner}/{repo}/contents/{filename}",
                    headers=self._headers(),
                )
                if resp.status_code != 200:
                    continue
                content = base64.b64decode(resp.json().get("content", "")).decode(
                    "utf-8", errors="replace"
                )
                manifests.append({
                    "file": filename,
                    "language": language,
                    "dependencies": self._extract_deps(filename, content),
                })
            except Exception as e:
                findings["errors"].append(f"deps {filename}: {e}")
        return manifests

    def _extract_deps(self, filename: str, content: str) -> List[str]:
        deps: List[str] = []
        if filename == "package.json":
            try:
                pkg = json.loads(content)
                for section in ("dependencies", "devDependencies"):
                    deps += [f"{k}@{v}" for k, v in pkg.get(section, {}).items()]
            except Exception:
                pass
        elif filename == "requirements.txt":
            deps = [
                line.strip()
                for line in content.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
        elif filename == "go.mod":
            deps = [
                line.strip()
                for line in content.splitlines()
                if line.strip().startswith(("require ", "\t"))
            ]
        elif filename == "Gemfile":
            deps = [
                line.strip()
                for line in content.splitlines()
                if line.strip().startswith("gem ")
            ]
        return deps[:50]

    async def _get_dependabot_alerts(self, client, owner, repo, findings) -> List[Dict]:
        """Fetch Dependabot vulnerability alerts (needs security_events scope)."""
        try:
            resp = await client.get(
                f"{self.api_base}/repos/{owner}/{repo}/dependabot/alerts",
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return [
                    {
                        "package": a.get("dependency", {}).get("package", {}).get("name"),
                        "severity": a.get("security_advisory", {}).get("severity"),
                        "cve": a.get("security_advisory", {}).get("cve_id"),
                        "state": a.get("state"),
                    }
                    for a in resp.json()
                ]
            findings["errors"].append(f"dependabot: HTTP {resp.status_code}")
        except Exception as e:
            findings["errors"].append(f"dependabot: {e}")
        return []

    def _summarize(self, findings: Dict) -> str:
        n_secrets = len(findings["exposed_secrets"])
        n_dep_alerts = len(findings["dependabot_alerts"])
        n_manifests = len(findings["outdated_deps"])
        return (
            f"Scanned {findings['repo']}: {n_secrets} exposed secrets, "
            f"{n_dep_alerts} Dependabot alerts, {n_manifests} dependency manifests analyzed."
        )

    def compute_threat_level(self, findings: Dict) -> int:
        """1-10 threat score from real findings."""
        score = 1
        score += min(len(findings.get("exposed_secrets", [])) * 3, 5)
        for alert in findings.get("dependabot_alerts", []):
            sev = str(alert.get("severity", "")).lower()
            score += {"critical": 3, "high": 2, "medium": 1}.get(sev, 0)
        return min(score, 10)
