from __future__ import unicode_literals
# -*- coding: utf-8 -*-
from scrapy.http.request import Request
from location.models import Offer, Source, OfferCategory
from datetime import datetime
from location.spiders.offer_spider import offerSpider
import logging
import re
import urlparse

log = logging.getLogger(__name__)

class MeilleursagentsSpider(offerSpider):
    name = "meilleursagents"
    start_urls = ['http://www.meilleursagents.com/immobilier/recherche/?redirect_url=&view_mode=&sort_mode=&transaction_type=369681778&buyer_search_id=&user_email=&place_ids[]=138724240&place_title=&item_types[]=369681781&item_types[]=369681782&item_area_min=&item_area_max=&budget_min=&budget_max=']


    offer_category_id = OfferCategory.objects.filter(name='location')[0].id
    source_id = Source.objects.filter(name="meilleursagents")[0].id

    def parse_next_page(self, response):
        try:
            for elmt in response.xpath('.//*[@id="body"]/div[@class="container-wide"]/div[contains(@class,"section")]/ul/li[@class="relative"]'):
                url = elmt.xpath('.//h2/a[@title]/@href').extract()[0]
                try:
                    html_id = int(re.match('.*/annonce-(\d+)/', url).group(1))
                except:
                    log.warning("No html_id for this element. Skipping it.")
                    continue

                check_offer = Offer.objects.filter(html_id=html_id).distinct()
                if Offer.objects.filter(html_id=html_id).count() == 0:
                    offer = Offer()
                    offer.first_crawl_date = datetime.now()
                else:
                    offer = check_offer[0]
                offer.html_id = html_id
                offer.source_id = self.source_id
                offer.offer_category_id = self.offer_category_id
                offer.url = "https:" + url
                offer.title = elmt.xpath('.//h2/a[@title]/@title').extract()[0]
                offer.area = re.match(u'^.*\s(\d+) m\xb2$',offer.title).group(1)
                try:
                    offer.price = re.match(u'(\d?\s\d+)+', elmt.xpath('.//div[contains(@class,"pull-right")]/div/strong/text()').extract()[0]).replace(' ', '')
                except:
                    offer.price = None
                offer.address = re.match(u'\s*(.*)\s*', elmt.xpath('.//div[@class="media-body"]//div[@class="pull-left"]/h2[a]/following::div[@class="muted ellipsis"]/text()').extract()[0]).group(1)
                offer.last_crawl_date = datetime.now()
                offer.save()
                yield Request(offer.url, callback=self.parse_one_annonce, meta={'offer':offer})
        except UnboundLocalError:
            print "Crawling done. Exiting..."
            exit()
        parse = urlparse.urlparse(response.url)
        t = True

        try:
            n = urlparse.parse_qs(parse.query)['p'][0]
        except KeyError:
            t = False
            next_page = response.url + '&p=2'
            yield Request(next_page,
                                callback=self.parse_next_page)

        if t:
            parsed = int(n)
            next_page = response.url[:-len(n)] + str(parsed + 1)

            yield Request(next_page,
                                callback=self.parse_next_page)

    def parse_one_annonce(self, response):
        offer = super(MeilleursagentsSpider, self).parse_one_annonce(response)
        try:
            offer.description = response.xpath('//div[@class="section"]/h2[contains(.,"Description")]/following::p/text()').extract()[0]
        except:
            log.warning("No description for this item")
            offer.description = ""
        offer.save()
