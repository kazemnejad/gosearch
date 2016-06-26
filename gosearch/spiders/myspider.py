import scrapy
import re
from goose import Goose
from stemming.porter2 import stem
from collections import Counter
class pythonSpider(scrapy.Spider):
    name = "python"
    start_urls = ["https://docs.python.org/3/"]
    allowed_domains = ["docs.python.org"]

    def parse(self, response, pr=None):
        print response.url
        for i in response.xpath('//a/@href').extract():
            if 'https://' in i or 'http://' in i:
                continue
            c = 0
            if re.match(r'(.*)\/(.*\.html)', response.url):
                c = 1
            urls = response.url.split("/")

            urls = '/'.join(urls[0:len(urls) - c - i.count("../")])
            if urls[-1]=='/':
                target=urls  + i.split("../")[-1]
            else:
                target = urls + '/' + i.split("../")[-1]
            #print "target:", target
            if target==pr :
                continue
            yield scrapy.Request(target, callback=lambda res: self.parse(res, response.url))

        g=Goose()
        article=g.extract(url=response.url)
        title=article.title
        main=article.cleaned_text
        title=re.findall(r'[A-Za-z0-9]\w*',title.lower())
        main=re.findall(r'[A-Za-z0-9]\w*',main.lower())


        for i in range(len(main)):
            main[i] = stem(main[i])
        for i in range(len(title)):
            title[i] = stem(title[i])
        main=Counter(main)
        title=Counter(title)
        for i in title:
            title[i]*=2
        main.update(title)
        result=main
        yield (response.url,result)