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
from utils.logging_config import setup_logging, get_logger
from cli.cli import main_cli


if __name__ == "__main__":
    # Initialize logging
    setup_logging()
    logger = get_logger(__name__)

    main_cli()
