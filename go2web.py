import argparse
import socket
from urllib.parse import urlparse
import ssl
import html2text
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import webbrowser
import hashlib
import pickle
from pathlib import Path

CACHE_FOLDER = Path.home() / '.go2web_cache'
CACHE_FOLDER.mkdir(exist_ok=True)

def generate_url_hash(url_string):
    return hashlib.md5(url_string.encode()).hexdigest()

def load_cached_data(url_string):
    url_hash = generate_url_hash(url_string)
    cache_path = CACHE_FOLDER / url_hash
    if cache_path.exists():
        with open(cache_path, 'rb') as f:
            return pickle.load(f)
    return None

def store_in_cache(url_string, response_data):
    url_hash = generate_url_hash(url_string)
    cache_path = CACHE_FOLDER / url_hash
    with open(cache_path, 'wb') as f:
        pickle.dump(response_data, f)



def convert_html_to_text(html_content):
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    return converter.handle(html_content)

def format_content(response_type, content_body):
    return convert_html_to_text(content_body)

def fetch_web_content(target_url, accept_header='text/html', remaining_redirects=10):
    if remaining_redirects <= 0:
        return None, "Redirect limit exceeded"

    url_hash = generate_url_hash(target_url)
    cached_content = load_cached_data(url_hash)
    if cached_content:
        return cached_content['content_type'], cached_content['body']

    try:
        parsed_url = urlparse(target_url)
        if not parsed_url.scheme:
            target_url = 'http://' + target_url
            parsed_url = urlparse(target_url)

        domain = parsed_url.netloc
        url_path = parsed_url.path or '/'
        if parsed_url.query:
            url_path += '?' + parsed_url.query

        request_headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': accept_header,
            'Connection': 'close',
            'Host': domain
        }

        http_request = f"GET {url_path} HTTP/1.1\r\n"
        http_request += '\r\n'.join(f'{key}: {value}' for key, value in request_headers.items())
        http_request += '\r\n\r\n'

        ssl_context = ssl.create_default_context()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            if parsed_url.scheme == 'https':
                connection = ssl_context.wrap_socket(connection, server_hostname=domain)
            connection_port = 443 if parsed_url.scheme == 'https' else 80
            connection.connect((domain, connection_port))
            connection.sendall(http_request.encode())

            raw_response = b''
            while True:
                chunk = connection.recv(4096)
                if not chunk:
                    break
                raw_response += chunk

        header_data, _, content = raw_response.partition(b'\r\n\r\n')
        headers = header_data.decode('utf-8', errors='ignore')

        first_line = headers.split('\r\n')[0]
        if '301' in first_line or '302' in first_line:
            for header_line in headers.split('\r\n'):
                if header_line.lower().startswith('location:'):
                    redirect_url = header_line.split(':', 1)[1].strip()
                    if not redirect_url.startswith('http'):
                        redirect_url = f"{parsed_url.scheme}://{domain}{redirect_url}"
                    return fetch_web_content(redirect_url, accept_header, remaining_redirects - 1)

        response_type = 'text/html'
        for header_line in headers.split('\r\n'):
            if header_line.lower().startswith('content-type:'):
                response_type = header_line.split(':', 1)[1].strip()
                break

        text_content = content.decode('utf-8', errors='ignore')

        store_in_cache(url_hash, {
            'content_type': response_type,
            'body': text_content
        })

        return response_type, text_content

    except Exception as error:
        print(f"Request error: {str(error)}")
        return None, None


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

def format_content(response_type, content_body):
    if 'application/json' in response_type:
        try:
            import json
            return json.dumps(json.loads(content_body), indent=2)
        except:
            return content_body
    return convert_html_to_text(content_body)

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
        accept = 'application/json' if arguments.json else 'text/html'
        content_type, content = fetch_web_content(arguments.url, accept)
        print(format_content(content_type, content))
    elif arguments.search:
        query = ' '.join(arguments.search)
        perform_search(query)

if __name__ == '__main__':
    execute_cli()