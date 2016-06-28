# -*- coding: utf-8 -*-

from abc import abstractmethod

import re
from collections import Counter
from scrapy.exceptions import DropItem

import nltk
from stemming.porter2 import stem

from gosearch.database.connection import db_session
from gosearch.database.models import Page, Word, Index, Position


class GosearchPipeline(object):
    @abstractmethod
    def process_item(self, item, spider):
        return item


class DuplicateCheckPipeline(GosearchPipeline):
    def process_item(self, item, spider):
        url = item["url"]
        if self.is_page_exist(url):
            raise DropItem("Duplicate page %s" % url)

        return item

    def is_page_exist(self, url):
        page = Page.query.filter_by(url=url).first()
        return page is not None


class TextNormalizationPipeline(GosearchPipeline):
    def process_item(self, item, spider):
        url = item["url"]
        article = item["article"]

        title = article.title
        main = article.cleaned_text
        title = re.findall(r'[A-Za-z0-9]\w*', title.lower())
        main = re.findall(r'[A-Za-z0-9]\w*', main.lower())

        for i in range(len(main)):
            main[i] = stem(main[i])
        for i in range(len(title)):
            title[i] = stem(title[i])
        delWord = dict(nltk.pos_tag(main))
        for i in delWord:
            if delWord[i] == 'DT' or delWord[i] == 'IN' or delWord[i] == 'CC' or delWord[i] == 'TO':
                for j in range(main.count(i)):
                    main.remove(i)

        delWord = dict(nltk.pos_tag(title))
        for i in delWord:
            if delWord[i] == 'DT' or delWord[i] == 'IN' or delWord[i] == 'CC' or delWord[i] == 'TO':
                for j in range(title.count(i)):
                    title.remove(i)
        print len(title)
        main_pos = {}
        for i in range(len(main)):
            if main_pos.get(main[i], 0) == 0:
                main_pos[main[i]] = [i]
            else:
                main_pos[main[i]].append(i)
        main = Counter(main)
        title = Counter(title)

        for i in title:
            title[i] *= 2
        main.update(title)

        return {
            "url": url,
            "title": article.title,
            "content": article.cleaned_text,
            "words": main,
            "wordspos": main_pos
        }


class StorePipeline(GosearchPipeline):
    def process_item(self, item, spider):
        url = item["url"]
        title = item["title"]
        content = item["content"]
        words = item["words"]
        words_pos = item["wordspos"]


        page = self.store_page(url, title, content)

        for word_text in words:
            score = words[word_text]
            word = self.store_word_if_not_exist(word_text)

            self.make_index(word, page, score)
            if word_text in words_pos:
                self.store_positions(word, page, words_pos[word_text])

    def store_page(self, url, title, content):
        page = Page(url, title, content)

        db_session.add(page)
        db_session.commit()

        return page

    def store_word_if_not_exist(self, text):
        word = Word.query.filter_by(text=text).first()
        if not word:
            word = Word(text)

            db_session.add(word)
            db_session.commit()

        return word

    def make_index(self, word, page, score):
        index = Index(score)
        index.page = page
        word.pages.append(index)

        db_session.commit()

    def store_positions(self, word, page, positions):
        for index in positions:
            position = Position(index)
            position.page = page
            word.ppages.append(position)

        db_session.commit()
