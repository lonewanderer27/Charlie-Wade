import os
import textwrap
from bs4 import BeautifulSoup
from typing import List
from cachetools import cached, TTLCache
from newspaper import Article, Config
import requests
from fastapi import FastAPI, Response
from pydantic import BaseModel
import uvicorn
from pprint import pprint

# ENVIRON VARIABLES
chapter_list_url = os.environ.get(
    'chapter_list_url',
    'https://m.informativestore.com/amazing-son-in-law/')

# NEWSPAPER CONFIG
config = Config()
config.browser_user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:10.0) Gecko/20100101 Firefox/10.0'
config.request_timeout = 10

# Cache Config
cache = TTLCache(maxsize=150, ttl=120)


class Text():
    text: str


class Messages(BaseModel):
    text: str


class SuccessResponse(BaseModel):
    messages: List[Messages]


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
) -> str | bool:
    try:
        url = filter(
            lambda link: True if link[1] == chapter_num else False, filtered_links)
        url = list(url)[0]
        url = url[0]
        article = get_article(url)
        return article.text
    except:
        return False


def get_latest_chapter(filtered_links: list) -> str | bool:
    try:
        url = filtered_links[-1][0]
        article = get_article(url)
        return article.text
    except:
        return False


def split_message(json: dict, text: str, n: int = 9):
    if n == 9:
        # makes sure that all the message is split evenly across 9 messages
        n = round(len(text) / 9)
    text_blocks = textwrap.wrap(text, width=n, break_long_words=False,
                                break_on_hyphens=False, drop_whitespace=True, replace_whitespace=False)
    for text_block in text_blocks:
        json['messages'].append({'text': f'{text_block}'},)
    return json


def error_on_retrieve() -> Response:
    json = {'messages': [
        {'text': 'An error has occured, please try again later.'}]}
    return json


def error_chapter_not_found(chapter: str):
    json = {'messages': [
        {'text': f'Error: Chapter {chapter} is not found.\n\nCheck if you entered the correct number.'}]}
    return json

app = FastAPI(title="Charlie Wade Backend API")


@app.get('/')
async def index():
    return 'Homepage'


@app.get('/chapter', description="Return a single chapter", response_model=SuccessResponse)
async def return_chapter(
    chapter: str,
):
    chapter_num = chapter
    try:

        json = {'messages': []}
        list_of_links_tuple = get_list_of_links_tuple()
        filtered_links = filter_list_of_links_tuple(list_of_links_tuple)
        chapter_text = get_chapter(filtered_links, chapter_num)

        response = split_message(
            json,
            chapter_text,   # type: ignore
            1000)
        print(f'Charlie Wade Chapter {chapter_num}:\n')
        pprint(response, indent=2)
        return response
    except Exception as e:
        print(e)
        return error_chapter_not_found(chapter_num)


@app.get('/chapters', description="Return a list of all available chapters", response_model=SuccessResponse)
async def return_chapters():
    json = {'messages': [{'text': 'Charlie Wade Chapters:'},]}

    list_of_links_tuple = get_list_of_links_tuple()
    filtered_links = filter_list_of_links_tuple(list_of_links_tuple)
    chapter_list = get_chapters(filtered_links)
    chapters = ""
    for chapter in chapter_list:
        chapters += f"{chapter} "

    response = split_message(json, chapters, 1996)
    pprint('Charlie Wade Chapters:\n')
    pprint(response, indent=2)
    return response


@app.get('/latest_chapter', description="Return the latest chapter", response_model=SuccessResponse)
def return_latest_chapter():
    try:
        json = {'messages': []}
        list_of_links_tuple = get_list_of_links_tuple()
        filtered_links = filter_list_of_links_tuple(list_of_links_tuple)
        chapter_text = get_latest_chapter(filtered_links)

        response = split_message(
            json,
            chapter_text,   # type: ignore
            1000)
        print('Latest Charlie Wade Chapter:\n')
        pprint(response, indent=2)
        return response
    except Exception as e:
        print(f'Error: {e}')
        return error_on_retrieve()


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0')


# list_of_links_tuple = get_list_of_links_tuple()
# filtered_links = filter_list_of_links_tuple(list_of_links_tuple)
# pprint(filtered_links, indent=2)
# chapters = get_chapters(filtered_links)
# print(get_chapter(filtered_links, "5093"))
