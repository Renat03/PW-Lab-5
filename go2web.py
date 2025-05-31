import argparse
import socket
from urllib.parse import urlparse
import ssl
import html2text
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import webbrowser


def convert_html_to_text(html_content):
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    return converter.handle(html_content)

def format_content(response_type, content_body):
    return convert_html_to_text(content_body)

def fetch_web_content(target_url):
    parsed_url = urlparse(target_url)
    if not parsed_url.scheme:
        target_url = 'http://' + target_url
        parsed_url = urlparse(target_url)

    domain = parsed_url.netloc
    url_path = parsed_url.path or '/'

    request_headers = {
        'Host': domain,
        'Connection': 'close'
    }

    http_request = f"GET {url_path} HTTP/1.1\r\n"
    http_request += '\r\n'.join(f'{key}: {value}' for key, value in request_headers.items())
    http_request += '\r\n\r\n'

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        if parsed_url.scheme == 'https':
            context = ssl.create_default_context()
            connection = context.wrap_socket(connection, server_hostname=domain)

        connection.connect((domain, 443 if parsed_url.scheme == 'https' else 80))
        connection.sendall(http_request.encode())

        response = b''
        while True:
            data = connection.recv(4096)
            if not data:
                break
            response += data

    _, _, body = response.partition(b'\r\n\r\n')
    return 'text/html', body.decode('utf-8', errors='ignore')


def perform_search(search_query):
    search_url = f"http://www.bing.com/search?q={quote_plus(search_query)}"
    content_type, html_data = fetch_web_content(search_url)

    soup = BeautifulSoup(html_data, 'html.parser')
    results = []

    for item in soup.find_all('li', class_='b_algo'):
        link = item.find('a')
        if link:
            results.append({
                'title': link.get_text(strip=True),
                'link': link['href']
            })
            if len(results) >= 10:
                break

    print(f"Top {len(results)} results:")
    for idx, item in enumerate(results, 1):
        print(f"{idx}. {item['title']}\n   {item['link']}")

    return results


def execute_cli():
    arg_parser = argparse.ArgumentParser(description='go2web - Web client utility')
    arg_parser.add_argument('-u', '--url', help='make an HTTP request to the specified URL and print the response')
    arg_parser.add_argument('-s', '--search', nargs='+', help='make an HTTP request to search the term using your favorite search engine and print top 10 results')
    arg_parser.add_argument('--json', action='store_true', help='Request JSON format')
    arguments = arg_parser.parse_args()

    if not any(vars(arguments).values()):
        arg_parser.print_help()
        return

    if arguments.url:
        content_type, content = fetch_web_content(arguments.url)
        print(format_content(content_type, content))

    elif arguments.search:
        query = ' '.join(arguments.search)
        perform_search(query)

if __name__ == '__main__':
    execute_cli()