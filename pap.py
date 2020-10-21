from __future__ import unicode_literals
# -*- coding: utf-8 -*-
from scrapy.http.request import Request
from location.models import Offer, Source, OfferCategory
import re
from location.spiders.offer_spider import offerSpider
from datetime import datetime

import logging

log = logging.getLogger(__name__)

class papSpider(offerSpider):
    name = "pap"
    max_price = 800
    start_urls = (
        # 'http://www.pap.fr/annonce/locations-appartement-paris-75-g439-jusqu-a-{0}-euros-a-partir-de-20-m2'.format(max_price),
        'http://www.pap.fr/annonce/locations-appartement-paris-75-g439',
    )
    offer_category_id = OfferCategory.objects.filter(name='location')[0].id
    source_id = Source.objects.filter(name='pap')[0].id

    def __init__(self, category="location"):
        super(self.__class__, self).__init__()
        self.offer_category_id = OfferCategory.objects.filter(name='location')[0].id


    def parse_next_page(self,response):
        try:
            for elmt in response.xpath('.//div[@class="box search-results-item"]'):
                html_id = elmt.xpath('.//a[@data-annonce]/@data-annonce').extract()[0].replace('false','False').replace('true','True')
                offer = Offer.objects.filter(html_id=html_id).distinct()
                if Offer.objects.filter(html_id=html_id).count() == 0:
                    offer = Offer()
                    offer.first_crawl_date = datetime.now()
                else:
                    offer = offer[0]

                offer.offer_category_id = self.offer_category_id
                offer.source_id = self.source_id
                offer.url = 'http://www.pap.fr' + elmt.xpath(".//div[@class='float-right']/a/@href").extract()[0]
                offer.title = elmt.xpath('.//span[@class="h1"]/text()').extract()[0]
                offer.price = elmt.xpath('.//span[@class="price"]/strong/text()').extract()[0][:-2].replace('.','').replace(' ','')
                offer.address = elmt.xpath('.//p[@class="item-description"]/strong/text()').extract()[0]
                offer.last_crawl_date = datetime.now()
                yield Request(offer.url, callback=self.parse_one_annonce, meta={'offer':offer})

        except UnboundLocalError:
            print "Crawling ended. Exiting..."
            exit()
        n = re.match('.*-(\d+)$',response.url)
        if n:
            page_suiv = response.url[:-len(n.groups()[0])] + str(int(n.groups()[0]) + 1)
        else:
            page_suiv = response.url + '-2'

        yield Request(page_suiv,
                              callback=self.parse_next_page)


    def parse_one_annonce(self, response):
        offer = super(papSpider, self).parse_one_annonce(response)
        surface = response.xpath('//*[contains(text(),"Surface")]/strong/text()').extract()
        offer.description = response.xpath('//p[@class="item-description"]/text()').extract()[0]
        try:
            offer.area = re.compile('(\D+)').sub('', surface[0])
        except:
            log.warning('No surface ! Skipping')
        offer.save()
