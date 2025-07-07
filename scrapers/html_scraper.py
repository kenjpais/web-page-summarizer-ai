from utils.parser_utils import parse_tables
from utils.utils import get_env, is_valid_url, contains_valid_keywords
from utils.parser_utils import parse_html

data_dir = get_env("DATA_DIR")


class HtmlScraper:
    def __init__(self, url):
        self.url = url

    def scrape(self):
        html = parse_html(self.url)
        self.scrape_valid_urls(html)
        # self.scrape_table_info()

    def scrape_valid_urls(self, soup):
        print("\n[*] Extracting URLs...")
        seen = set()
        with open(f"{data_dir}/urls.txt", "w") as file:
            for a_tag in soup.find_all("a", href=True):
                text, url = a_tag.get_text(strip=True), a_tag["href"].strip()
                if (
                    url
                    and url not in seen
                    and is_valid_url(url)
                    and contains_valid_keywords([text, url])
                ):
                    file.write(url + "\n")
                    seen.add(url)

    def scrape_table_info(self):
        html = parse_html(self.url)
        df = parse_tables(html)
        df.to_pickle(f"{data_dir}/feature_gate_table.pkl")


def scrape_html(url):
    print("\n[*] Parsing...")
    HtmlScraper(url).scrape()
