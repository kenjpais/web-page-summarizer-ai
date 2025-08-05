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
import sys
from utils.logging_config import setup_logging, get_logger


def show_help():
    """Display usage information."""
    print(
        """
Release Page Summarizer

Usage: python main.py [OPTIONS] <release_page_url_or_file>

Options:
    --help, -h         Show this help message

Arguments:
    release_page_url_or_file    URL to a live release page or path to HTML file

Examples:
    # Process a live release page
    python main.py https://amd64.origin.releases.ci.openshift.org/releasestream/4-stable/release/4.19.0
    
    # Process a local HTML file
    python main.py /path/to/release_page.html

Environment Variables:
    GH_API_TOKEN       GitHub API token (required)
    JIRA_SERVER        JIRA server URL (required)
    LLM_PROVIDER       LLM provider: local, gemini (default: local)
    GOOGLE_API_KEY     Google API key (required for Gemini)
"""
    )


if __name__ == "__main__":
    # Initialize logging
    setup_logging()
    logger = get_logger(__name__)

    try:
        # Parse command line arguments
        if len(sys.argv) < 2:
            show_help()
            sys.exit(1)

        command = sys.argv[1]

        if command in ["--help", "-h"]:
            show_help()
            sys.exit(0)
        elif command.startswith("--"):
            print(f"Unknown option: {command}")
            show_help()
            sys.exit(1)
        else:
            # Validate input source
            source = command

            # Basic input validation
            if not source or len(source.strip()) == 0:
                print("Error: Source cannot be empty")
                sys.exit(1)

            # Execute main pipeline
            logger.info(f"Starting release page analysis for: {source}")
            summarize_release_page_from_url(source)
            logger.info("Application completed successfully")

            sys.exit(0)

    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"Application failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)
