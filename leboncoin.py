from __future__ import unicode_literals
# -*- coding: utf-8 -*-
from scrapy.http.request import Request
from location.models import Offer, Source, OfferCategory
from datetime import datetime
from location.spiders.offer_spider import offerSpider
import urlparse
import re

class leboncoinSpider(offerSpider):
    name = "leboncoin"
    max_price = 800
    start_urls = ()

    source_id = Source.objects.filter(name='leboncoin')[0].id

    map_category_to_url = {
        'location': 'https://www.leboncoin.fr/locations/offres/ile_de_france/paris/?f=a&th=1&mre=&sqs=1&ret=2',
        'colocation': 'https://www.leboncoin.fr/colocations/offres/ile_de_france/?th=1&location=Paris&parrot=0',
        'telephone': 'https://www.leboncoin.fr/telephonie/offres/ile_de_france/?th=1&q=note%204&parrot=0&ps=8&pe=12'
    }

    def __init__(self, category="location"):
        super(self.__class__, self).__init__()
        self.start_urls = (self.map_category_to_url[category],)
        self.offer_category_id = OfferCategory.objects.filter(name=category)[0].id

    def parse_next_page(self, response):
        try:
            tags = response.xpath('.//li[@itemtype="http://schema.org/Offer"]')
            if not len(tags):
                exit()
            for elmt in tags:
                html_id = elmt.xpath('.//div[@class="saveAd"]/@data-savead-id').extract()[0]
                check_offer = Offer.objects.filter(html_id=html_id).distinct()
                if Offer.objects.filter(html_id=html_id).count() == 0:
                    offer = Offer()
                    offer.first_crawl_date = datetime.now()
                else:
                    offer = check_offer[0]

                offer.html_id = html_id
                offer.source_id = self.source_id
                offer.offer_category_id = self.offer_category_id
                offer.url = 'http:' + elmt.xpath('.//a/@href').extract()[0]
                offer.title = elmt.xpath('.//section[@class="item_infos"]/h2/text()').extract()[0].strip()
                try:
                    offer.price = elmt.xpath('.//div[@class="price"]/text()').extract()[0].strip()
                except:
                    try:
                        offer.price = elmt.xpath('.//h3[@class="item_price"]/@content').extract()[0].strip()
                    except:
                        pass # there's definitely no price down here
                try:
                    offer.address = elmt.xpath('.//p[@itemtype="http://schema.org/Place"]/text()').extract()[0].strip()
                except:
                    pass
                offer.last_crawl_date = datetime.now()
                offer.save()
                yield Request(offer.url, callback=self.parse_one_annonce, meta={'offer':offer})
        except UnboundLocalError:
            print "Crawling done. Exiting..."
            exit()
        parse = urlparse.urlparse(response.url)
        t = True

        try:
            n = urlparse.parse_qs(parse.query)['o'][0]
        except KeyError:
            t = False
            next_page = response.url + '&o=2'
            yield Request(next_page,
                                callback=self.parse_next_page)

        if t:
            parsed = int(n)
            next_page = response.url[:-len(n)] + str(parsed + 1)

            yield Request(next_page,
                                callback=self.parse_next_page)


    def parse_one_annonce(self, response):
        offer = super(leboncoinSpider, self).parse_one_annonce(response)
        surface = response.xpath('//span[text()="Surface"]/following::span/text()').extract()
        description = response.xpath('//div/p[@itemprop="description"]').extract()
        try:
            offer.area = re.compile('(\D+)').sub('', surface[0])
        except:
            pass
        offer.description = re.compile('<.*?>').sub('', description[0])
        offer.save()
