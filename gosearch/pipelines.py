# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
from abc import abstractmethod

import re
from collections import Counter

from stemming.porter2 import stem


class GosearchPipeline(object):
    @abstractmethod
    def process_item(self, item, spider):
        return item


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
        main = Counter(main)
        title = Counter(title)
        for i in title:
            title[i] *= 2
        main.update(title)

        return {
            "url": url,
            "words": main
        }

class StorePipeline(GosearchPipeline):
    def process_item(self, item, spider):
        words = item["words"]
        url = item["url"]

        print words
        print url




