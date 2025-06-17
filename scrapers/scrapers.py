from scrapers.jira_scraper import JiraScraper
from scrapers.github_scraper import GithubScraper

SOURCE_SCRAPERS_MAP = {
    "JIRA": JiraScraper,
    "GITHUB": GithubScraper,
}
