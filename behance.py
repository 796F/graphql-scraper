from lxml.html import fromstring
import requests
import time
import os
import json
import random
import argparse

base_uri = 'https://www.behance.net'
headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,'\
    'image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ('\
    'KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36', 'authority': base_uri.split('://')[-1],
}


def generate_cookie():
    bcp = {
        'bcp': '{0}cfb{1}f-{2}cba-{2}c{3}-b{3}d-{3}ba{2}c{4}'.format(
            random.choice(range(200, 999)),
            random.choice(range(1, 9)),
            random.choice(range(1, 9)),
            random.choice(range(20, 99)),
            random.choice(range(234567, 987654)),
        )
    }
    
    return bcp


def get_time_option(chosenOption):
    sort_by_dict = {
        '':           '',
        'Today':      'today',
        'This Week':  'week',
        'This Month': 'month',
        'All Time':   'all',
    }
    
    return sort_by_dict[chosenOption]


def get_sort_by_option(chosenOption):
    sort_by_dict = {
        '':                 '',
        'Curated':          'featured_date',
        'Most Appreciated': 'appreciations',
        'Most Viewed':      'views',
        'Most Discussed':   'comments',
        'Most Recent':      'published_date',
    }
    
    return sort_by_dict[chosenOption]


def get_crative_option(chosenOption):
    sort_by_dict = {
        '':                  '',
        'Photography':       'photography',
        'Industrial Design': 'industrial design',
    }
    
    return sort_by_dict[chosenOption]


def process_item(listingItems, searchTerm, count=0):
    for url, [name, iD] in listingItems.items():
        tree = fromstring(s.get(url, cookies={'ilo0': 'true'}).text)
        images = tree.xpath('//div[@id="project-modules"]/div//img[not(contains(@src, "blank.png"))]/@src')
        images.extend(tree.xpath('//div[@id="project-modules"]/div//img[not(contains(@data-src, "blank.png"))]/@data-src'))
        if not images: continue
        
        title = "{0} - {1}".format(tree.xpath('//h1/text()')[0], searchTerm.title())
        tags = tree.xpath('//ul[contains(@class, "ProjectTags")]/li/a/text()')
        tools = tree.xpath('//ul[contains(@class, "Tools")]/li/a/text()')
        try: owner = tree.xpath('//a[contains(@class, "userName")]/text()')[0]
        except: continue
        data_json = {'tags': tags, 'tools': tools, 'title': title, 'owner': owner}
        if not os.path.isdir('projects//' + iD): os.makedirs('projects//' + iD)
        with open('projects//{0}//data.json'.format(iD, ), 'w+') as outfile:
            outfile.write(json.dumps(data_json, indent=4))
        count += 1
        
        for i, img in enumerate(images):
            with open('projects//{0}//img{1:03}.{2}'.format(iD, i + 1, img.split('.')[-1]), 'wb') as outfile:
                outfile.write(requests.get(img).content)
            time.sleep(0.5)
        
        print("{0:02}: {1}".format(count, title))
        if count == 50: break
        time.sleep(0.5)
    
    return count


def main(options):
    if not os.path.isdir('projects'): os.makedirs('projects')
    params = {'field': options[0], 'sort': options[1], 'time': options[2], 'search': options[3]}
    [params.pop(key) for key, value in params.copy().items() if value == '']
    tree = fromstring(s.get(base_uri + '/search', params=params, cookies={'ilo0': 'true'}).text)
    _, scriptProjects = params.pop('search'), json.loads(tree.xpath('//script[@id="beconfig-store_state"]/text()')[0])
    count = process_item({x["url"]:[x["name"], str(x["id"])] for x in scriptProjects["search"]["content"]["projects"]}, options[3])
    _postHead = {'content-type': 'application/json', 'x-bcp': s.cookies.get_dict()['bcp'], 'x-requested-with': 'XMLHttpRequest'}
    json_data = {
        'query': '''
            query GetProjectSearchResults($query: query, $filter: SearchResultFilter, $first: Int!, $after: String) {
                search(query: $query, type: PROJECT, filter: $filter, first: $first, after: $after) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        ... on Project {
                            id
                            name
                            url
                            sourceFiles {
                                ...sourceFileFields
                            }
                        }
                    }
                }
            }
            fragment sourceFileFields on SourceFile {projectId}
        ''',
        'variables': {
            'query': options[3],
            'filter': params,
            'first': 48,
            'after': 'NDk=',
        }
    }
    
    response = s.post(base_uri + '/v3/graphql', headers=_postHead, json=json_data).json()['data']
    process_item({x["url"]:[x["name"], str(x["id"])] for x in response['search']['nodes']}, options[3], count)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Behance project scrapper.')
    parser.add_argument('--search-term', type=str, required=True, help='Enter SearchTerm')
    parser.add_argument(
        '--creative-field', type=str, default='',
        choices=['Photography', 'Industrial Design'],
        help='Enter Creative Field, default (All Creative Fields)'
    )
    parser.add_argument(
        '--sort-by', type=str, default='',
        choices=['Recommended', 'Curated', 'Most Appreciated', 'Most Viewed', 'Most Discussed', 'Most Recent'],
        help='Enter Sort-By Option, default (Recommended)'
    )
    parser.add_argument(
        '--time', type=str, default='',
        choices=['Today', 'This Week', 'This Month', 'All Time'],
        help='Enter Sort Time Option, default (empty)'
    )
    
    parsed = parser.parse_args()
    s = requests.session()
    s.headers = headers
    s.cookies.update(generate_cookie())
    main([
        get_crative_option(parsed.creative_field),
        get_sort_by_option(parsed.sort_by),
        get_time_option(parsed.time),
        parsed.search_term
    ])
