# Release Page Summarizer AI

A Python-based web scraper and summarization tool designed to extract, filter, and analyze data from OpenShift release stream pages. The tool offers integration with JIRA and GitHub, supporting both issue-id based and username based data retrieval and summarization. Supports environment-based configuration, and includes automated testing and CI workflows.

---

## Key Features

- **Automated Web Scraping**: Extracts metadata and release information from OpenShift release page urls and/or JIRA and/or GITHUB urls and correlates related release data under matching projects.
- **Summary Generation**: Creates structured summaries of release data using LLM (Local Mistral or Google Gemini).
- **Configurable Data Sources**: Supports multiple backends including GitHub (PRs, Commits) and JIRA (summary and description fields of all JIRA Artifacts). Fetches publicly available data only.
- **Secure Environment Management**: Credentials and configuration managed via `.env`.
- **Test Coverage**: Includes unit tests for core logic and controllers.
- **CI/CD Integration**: GitHub Actions used for continuous integration and scheduled execution.

---

## Getting Started

### Prerequisites

- Python 3.8+
- `pip` package manager
- Ollama (for local LLM) or Google API Key (for Gemini)

### Environment Setup

1. Set up required environment variables:
```bash
# Required for GitHub access
export GH_API_TOKEN=your_github_api_token_here

# Required only if using Gemini as LLM
export GOOGLE_API_KEY=your_gemini_token_here
```

Get your github API key here:
https://docs.github.com/en/rest/authentication/authenticating-to-the-rest-api

Get your gemini API key here:
https://ai.google.dev/gemini-api/docs/api-key

2. Install dependencies and set up the environment:
```bash
sh setup.sh
```

3. Start the LLM server (if using local Mistral):
```bash
sh start_llm.sh
```

For detailed LLM setup instructions, refer to `LLM_SETUP.md`.

## Usage

The tool provides three main commands:

### 1. Scrape Data
```bash
# Scrape from a URL
python main.py scrape --url <release_page_url>

# Scrape from JIRA
python main.py scrape --issue-ids "ISSUE-1,ISSUE-2" --jira-server "https://jira.example.com"

# Scrape from GitHub with authentication
python main.py scrape --url <release_page_url> --github-token <token> --github-server "https://github.com"

# Enable filtering while scraping
python main.py scrape --url <url> --filter-on
```

### 2. Correlate Data
```bash
# Correlate previously scraped data
python main.py correlate
```

### 3. Generate Summaries
```bash
# Generate summaries from correlated data
python main.py summarize --url <url>

# Generate summaries with specific data sources
python main.py summarize --url <url> --issue-ids "ISSUE-1,ISSUE-2" --github-token <token>
```

### Common Options

- `--filter-on`: Enable filtering of data based on configured rules
- `--url`: URL to scrape data from
- `--issue-ids`: Comma-separated list of JIRA issue IDs
- `--usernames`: Comma-separated list of JIRA usernames to fetch data for
- `--jira-server`: JIRA server URL
- `--jira-username`: JIRA username (optional)
- `--jira-password`: JIRA password (optional)
- `--github-server`: GitHub server URL
- `--github-token`: GitHub API token
- `--github-username`: GitHub username (optional)
- `--github-password`: GitHub password (optional)

## Output

Generated summaries and data will be stored in the following locations:
- Scraped data: `data/`
- Summaries: `data/summaries/`

## Running Tests

```bash
# Make the test script executable
chmod +x run_scraper_tests.sh

# Run the tests
./run_scraper_tests.sh
```

## Configuration

- To disable summary generation, set `SUMMARIZE_ENABLED=False` in your environment.
- For LLM configuration, refer to `LLM_SETUP.md`.
- Additional configuration options can be found in the `config/` directory.
