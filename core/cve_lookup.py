# core/cve_lookup.py
"""
Utility module to look up active CVEs asynchronously from the NVD CVE API.
"""
import aiohttp
import asyncio
import logging
from typing import List, Dict
from langchain_core.tools import tool

logger = logging.getLogger("fusion.cve")
CVE_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

async def get_cves_async(keyword: str, max_results: int = 5) -> List[Dict]:
    """Fetch CVE details asynchronously by keyword search."""
    params = {
        "keywordSearch": keyword,
        "resultsPerPage": max_results
    }
    logger.info(f"Querying NVD CVE API for keyword: '{keyword}'...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(CVE_API_URL, params=params, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"NVD CVE API returned status code {resp.status}")
                    return []
                data = await resp.json()
        
        results = []
        for vuln in data.get("vulnerabilities", []):
            cve = vuln.get("cve", {})
            cve_id = cve.get("id", "")
            
            # Extract CVSS score
            cvss_score = 0.0
            metrics = cve.get("metrics", {})
            for version_key in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                if version_key in metrics and metrics[version_key]:
                    cvss_data = metrics[version_key][0].get("cvssData", {})
                    cvss_score = cvss_data.get("baseScore", 0.0)
                    break
            
            # Extract description
            descriptions = cve.get("descriptions", [])
            description = ""
            for desc in descriptions:
                if desc.get("lang") == "en":
                    description = desc.get("value", "")[:250] + "..."
                    break
            
            results.append({
                "id": cve_id,
                "cvss_score": cvss_score,
                "severity": "CRITICAL" if cvss_score >= 9.0 else
                            "HIGH" if cvss_score >= 7.0 else
                            "MEDIUM" if cvss_score >= 4.0 else "LOW",
                "description": description
            })
        
        # Sort by CVSS score descending
        return sorted(results, key=lambda x: x["cvss_score"], reverse=True)
    except Exception as e:
        logger.error(f"Error querying NVD CVE API: {e}")
        return []

@tool
def get_cves(keyword: str, max_results: int = 5) -> str:
    """Fetch CVE details asynchronously by keyword search.
    
    Runs the async HTTP call in a dedicated thread to avoid blocking
    or deadlocking the main asyncio event loop.
    """
    import concurrent.futures
    import json
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, get_cves_async(keyword, max_results))
        return json.dumps(future.result(timeout=30))
