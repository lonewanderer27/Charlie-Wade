from typing import Union
import os
import textwrap
from bs4 import BeautifulSoup
from cachetools import cached, TTLCache
from newspaper import Article, Config
import requests
from flask import Flask, request, jsonify
from flask.wrappers import Response
from pprint import pprint

# ENVIRON VARIABLES
chapter_list_url = os.environ.get(
    'chapter_list_url',
    'https://m.informativestore.com/the-amazing-son-in-law/')

# NEWSPAPER CONFIG
config = Config()
config.browser_user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:10.0) Gecko/20100101 Firefox/10.0'
config.request_timeout = 10

# Cache Config
cache = TTLCache(maxsize=150, ttl=120)

def get_article(url: str) -> Article:
    '''Returns text content of a webpage'''
    article = Article(url=url, config=config)
    article.download()
    article.parse()
    return article

@cached(cache)
def get_a_tags() -> list[BeautifulSoup]:
    '''Returns all anchor tags from a page'''
    page = requests.get(chapter_list_url)
    soup = BeautifulSoup(page.content, 'html.parser')
    anchor_tags = soup.find_all("a", class_="wp-block-button__link")
    return anchor_tags

def get_list_of_links_tuple() -> list:
    '''Returns a list of links set'''
    links = map(
        lambda a_tag: (a_tag.get('href'), a_tag.text), get_a_tags()
    )
    return list(links)

def filter_list_of_links_tuple(links: list) -> list:
    '''
    Loops over list of sets
    Returns each set, with the second item in the set shortened to its
    chapter string.
    '''
    filtered_links = []
    for link in links:
        words = link[1].split(" ")
        if len(words[-1]) == 4:
            filtered_links.append((link[0], words[-1]))
    return filtered_links

def get_chapters(filtered_links: list) -> list:
    '''Returns the list of chapters from list of links set'''
    chapters = map(lambda link: link[1], filtered_links)
    return list(chapters)

def get_links(filtered_links: list) -> list:
    '''Returns the list of links from list of links set'''
    links = map(lambda link: link[0], filtered_links)
    return list(links)

def get_chapter(
        filtered_links: list, 
        chapter_num: str
    ) -> Union[str, bool]:
    try:
        url = filter(lambda link: True if link[1] == chapter_num else False, filtered_links)
        url = list(url)[0]
        url = url[0]
        article = get_article(url)
        return article.text
    except:
        return False

def get_latest_chapter(filtered_links: list) -> Union[str, bool]:
    try:
        url = filtered_links[-1][0]
        article = get_article(url)
        return article.text
    except:
        return False

def split_message(json: dict, text: str, n: int = 9):
    if n == 9:
        n = round(len(text) / 9)    # makes sure that all the message is split evenly across 9 messages
    text_blocks = textwrap.wrap(text, width=n, break_long_words=False, break_on_hyphens=False, drop_whitespace=True, replace_whitespace=False)
    for text_block in text_blocks:
        json['messages'].append({'text': f'{text_block}'},)
    return json

def arg_is_none(message: str):
    print(f'Error 400: {message}')
    return Response(
        message,
        status=400
    )

def error_on_retrieve() -> Response:
    json = {'messages': [{'text': 'An error has occured, please try again later.'}]}
    response = jsonify(json)
    return response

def error_chapter_not_found(chapter: str) -> Response:
    json = {'messages': [{'text': f'Error: Chapter {chapter} is not found.\n\nCheck if you entered the correct number.'}]}
    response = jsonify(json)
    response.status_code = 404
    return response


app = Flask(__name__)

@app.route('/')
def index():
    return 'Homepage'

@app.route('/chapter')
def return_chapter():
    chapter_num = request.args.get('chapter', None)
    if not chapter_num:
        return arg_is_none('Error: chapter arg is missing')
    json = {'messages': []}
    try:
        list_of_links_tuple = get_list_of_links_tuple()
        filtered_links = filter_list_of_links_tuple(list_of_links_tuple)
        chapter_text = get_chapter(filtered_links, chapter_num)
    except Exception as e:
        print(f'Error: {e}')
        return error_chapter_not_found(chapter_num)

    response = jsonify(
                    split_message(
                        json, 
                        chapter_text,   # type: ignore 
                        1000)
                    ) 
    print(f'Charlie Wade Chapter {chapter_num}:\n')
    pprint(response.json, indent=2)
    return response

@app.route('/chapters')
def return_chapters():
    try:
        json = {'messages':[{'text': 'Charlie Wade Chapters:'},]}
        
        list_of_links_tuple = get_list_of_links_tuple()
        filtered_links = filter_list_of_links_tuple(list_of_links_tuple)
        chapter_list = get_chapters(filtered_links)
        chapters = ""
        for chapter in chapter_list:
            chapters += f"{chapter} "

        response = jsonify(split_message(json, chapters, 1996))
        pprint('Charlie Wade Chapters:\n')
        pprint(response.json, indent=2)
        return response
    except Exception as e:
        print(f'Error: {e}')
        return error_on_retrieve()

@app.route('/latest_chapter')
def return_latest_chapter():
    try:
        json = {'messages': []}
        list_of_links_tuple = get_list_of_links_tuple()
        filtered_links = filter_list_of_links_tuple(list_of_links_tuple)
        chapter_text = get_latest_chapter(filtered_links)
        
        response = jsonify( split_message(
                        json, 
                        chapter_text,   # type: ignore 
                        1000)) 
        print('Latest Charlie Wade Chapter:\n')
        pprint(response.json, indent=2)
        return response
    except Exception as e:
        print(f'Error: {e}')
        return error_on_retrieve()

        
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)




# list_of_links_tuple = get_list_of_links_tuple()
# filtered_links = filter_list_of_links_tuple(list_of_links_tuple)
# pprint(filtered_links, indent=2)
# chapters = get_chapters(filtered_links)
# print(get_chapter(filtered_links, "5093"))