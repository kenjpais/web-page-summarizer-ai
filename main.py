from controllers.summarize_url_controller import summarize_release_page_from_url

"""
Release Page Summarizer - Main Entry Point

This application processes OpenShift release pages to extract, correlate, and summarize
development activity including JIRA issues, GitHub PRs/commits, and feature gate information.

The pipeline performs the following steps:
1. HTML Parsing - Extract URLs from release pages
2. URL Filtering - Categorize URLs by source type (GitHub, JIRA)
3. Data Scraping - Fetch detailed information from each source
4. Correlation - Link related items across sources using JIRA IDs
5. Summarization - Generate human-readable reports using LLM analysis

Usage:
    python main.py <release_page_url_or_file>

Examples:
    # Process a live release page
    python main.py https://amd64.origin.releases.ci.openshift.org/releasestream/4-stable/release/4.19.0

    # Process a local HTML file
    python main.py /path/to/saved/release_page.html

Requirements:
    - GitHub API token (GH_API_TOKEN environment variable)
    - JIRA server access (JIRA_SERVER environment variable)
    - LLM service running (for summarization)

The application creates structured output files in the configured data directory
including JSON data files, Markdown reports, and final summaries.
"""

import runner
from utils.logging_config import setup_logging, get_logger

if __name__ == "__main__":
    import sys

    # Initialize logging system for the entire application
    setup_logging()
    logger = get_logger(__name__)

    # Validate command line arguments
    if len(sys.argv) < 2:
        logger.error(
            "Usage: python main.py <release_page_url_or_file>\n"
            "       \n"
            "       Examples:\n"
            "         python main.py https://releases.ci.openshift.org/...\n"
            "         python main.py /path/to/release_page.html\n"
            "       \n"
            "       The input can be either a URL to a live release page\n"
            "       or a path to a saved HTML file."
        )
        sys.exit(1)
    else:
        # Execute the main pipeline with the provided source
        summarize_release_page_from_url(sys.argv[1])
