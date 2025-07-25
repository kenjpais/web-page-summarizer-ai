# Release Page Summarizer

A Python-based web scraper designed to extract, filter, and summarize data from OpenShift release stream pages. The tool integrates with third-party systems like JIRA and GitHub, supports environment-based configuration, and includes automated testing and CI workflows.

---

## Key Features

- **Automated Web Scraping**: Extracts metadata and release information from OpenShift release pages and correlates related release data under matching projects.
- **Summary Generation**: Creates structured summaries of release data.
- **Configurable Data Sources**: Supports multiple backends including GitHub(ie. PRs, Commits) and JIRA(ie. summary and description fields of all JIRA Artifacts). Fetches publicly available data only.
- **Secure Environment Management**: Credentials and configuration managed via `.env`.
- **Test Coverage**: Includes unit tests for core logic and controllers.
- **CI/CD Integration**: GitHub Actions used for continuous integration and scheduled execution.

---

## Getting Started

### Prerequisites

- Python 3.8+
- `pip` package manager

#### Setup
export GH_API_TOKEN=your_github_api_token_here (needs a GITHUB API token to run github client)

sh setup.sh
sh start_llm.sh

#### Run
python main.py <release_page_url_or_file> (Summary will be generated under ~/data/summaries/<release-version>/)

#### Run Tests
chmod +x run_scraper_tests.sh
./run_scraper_tests.sh

If you just want to use the scraper and not generate summaries, you can set SUMMARIZE_ENABLED flag as False.
