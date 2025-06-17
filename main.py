import runner

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(
            "Usage: python script.py <release_page_html_file> or \npython script.py <url>"
        )
    else:
        runner.run(sys.argv[1])
