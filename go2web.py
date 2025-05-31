#!/usr/bin/env python3
import argparse

def main():
    parser = argparse.ArgumentParser(description='go2web - HTTP client')
    parser.add_argument('-u', '--url', help='URL to fetch')
    parser.add_argument('-s', '--search', nargs='+', help='Search term')
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return

    if args.url:
        print(f"Would fetch URL: {args.url}")
    elif args.search:
        print(f"Would search for: {' '.join(args.search)}")

if __name__ == '__main__':
    main()