# core/cve_lookup.py
"""
Utility module to look up active CVEs asynchronously from the NVD CVE API.
"""
import aiohttp
import asyncio
import logging
from typing import List, Dict

logger = logging.getLogger("argus.cve")
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

def get_cves(keyword: str, max_results: int = 5) -> List[Dict]:
    """Synchronous wrapper for tool calls (e.g. LangChain tools)."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # Running inside another loop (like FastAPI), need to use a background task or run_coroutine_threadsafe
        # But for simple scripts, we can use loop.run_until_complete
        future = asyncio.run_coroutine_threadsafe(get_cves_async(keyword, max_results), loop)
        return future.result()
    else:
        return loop.run_until_complete(get_cves_async(keyword, max_results))
