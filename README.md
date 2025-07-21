# Release Page Summarizer

A Python-based web scraper designed to extract, filter, and summarize data from OpenShift release stream pages. The tool integrates with third-party systems like JIRA and GitHub, supports environment-based configuration, and includes automated testing and CI workflows.

---

## Key Features

- **Automated Web Scraping**: Extracts metadata and release information from OpenShift release pages and correlates related release data under matching projects.
- **Summary Generation**: Creates structured summaries of release data.
- **Configurable Data Sources**: Supports multiple backends including GitHub and JIRA.
- **Secure Environment Management**: Credentials and configuration managed via `.env`.
- **Test Coverage**: Includes unit tests for core logic and controllers.
- **CI/CD Integration**: GitHub Actions used for continuous integration and scheduled execution.

---

## Getting Started

### Prerequisites

- Python 3.8+
- `pip` package manager

#### Needs a GITHUB API token to run github client
export GH_API_TOKEN=your_github_api_token_here

#### Run
python main.py <release_page_url_or_file>

#### Run Tests
chmod +x run_scraper_tests.sh
./run_scraper_tests.sh
