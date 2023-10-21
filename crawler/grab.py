import click
import csv
import requests
import sys
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs


def parse_url(url):
    """
    Parse a URL into base URL and query parameters.
    
    Args:
        url (str): The URL to be parsed.
        
    Returns:
        tuple: (base_url, query_params)
        
    >>> parse_url("https://www.peticie.com/signatures.php?tunnus=peticia&page_number=257&num_rows=100")
    ('https://www.peticie.com/signatures.php', {'tunnus': 'peticia', 'page_number': '257', 'num_rows': '100'})
    """
    # Parse the URL
    parsed_url = urlparse(url)
    
    # Extract the base URL without query parameters
    base_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
    
    # Parse the query parameters into a dictionary
    query_params = parse_qs(parsed_url.query)
    
    # Convert list values to single values
    for key, value in query_params.items():
        if len(value) == 1:
            query_params[key] = value[0]
    
    return base_url, query_params

def extract_data_from_page(soup):
    table = soup.find('table', {'id': 'signatures'})
    rows = table.find_all('tr')
    
    data = []
    for row in rows[1:]:  # Skip header row
        columns = row.find_all('td')
        if "Podpisaný rozhodol" in columns[1].text:  # Skip anonymous entries
            data.append(['', '', '', '']) 
        else:
            name = columns[1].text.strip()
            city = columns[2].text.strip()
            comment = columns[3].text.strip()
            date = columns[4].text.strip()
            data.append([name, city, comment, date])
    return data

def save_to_csv(data, filename="petition_data.csv"):
    with open(filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(data)

@click.command()
@click.argument('url', type=str)
@click.option('--page', type=int, default=1, help="The starting page number for scraping. Defaults to 1.")
@click.option('--num-rows', type=int, default=100, help="The number of rows to scrape per page. Defaults to 100.")
@click.option('--csv-filename', type=str, default=None, help="The name of the output CSV file. Defaults to 'petition_name_form_url.csv'.")
def main(url, page, num_rows, csv_filename):
    """
    A script to scrape petition signatures from peticie.com.
    """
    page_number = page 

    base_url, query_params = parse_url(url)
    query_params['num_rows'] = num_rows

    if csv_filename is None:
        if query_params['tunnus'] is None:
            print("Can't find petition name, do you have the right URL?", file=sys.stderr)
            sys.exit(1)
        csv_filename = query_params['tunnus'] + '.csv'

    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Name", "City", "Comment", "Date"])
    

    stats = {
        'rows': 0,
        'annonymous_rows': 0,
    }
    
    print(f"URL: {base_url}?{'&'.join(f'{key}={value}' for (key, value) in query_params.items())}")
    
    while True:
        query_params['page_number'] = page_number
        response = requests.get(base_url, params=query_params)
        print('.', end='', flush=True)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        data = extract_data_from_page(soup)
        if not data:
            break

        stats['rows'] += len(data)
        stats['annonymous_rows'] += len([row for row in data if row == ['', '', '', '']])
        
        save_to_csv(data, csv_filename)
        
        # Check if there's a next page
        pagination = soup.find('ul', {'class': 'pagination'})
        next_page = pagination.find('a', {'class': 'page-link'}, string=" »")
        if next_page:
            page_number += 1
        else:
            break

    print(f"\nRows: {stats['rows']},\nAnonymous: {stats['annonymous_rows']},\nPages: {page_number}")


if __name__ == "__main__":
    main()

