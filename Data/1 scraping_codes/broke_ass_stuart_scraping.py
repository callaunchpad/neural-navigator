from bs4 import BeautifulSoup
import requests
import pandas as pd

def events(url, page, base):
    event_titles = []
    event_imgs = []
    event_locs = []
    event_times = []
    event_thru = []
    event_bas_url = []

    for i in range(1, 1000):
        response = requests.get(url+page+str(i))

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            event_cards = soup.find_all("div", class_="event-card")
            if len(event_cards) == 0:
                break

            for event_card in event_cards:
                title = event_card.find("span", class_="ds-listing-event-title-text")
                if title:
                    event_titles.append(title.get_text())
                else:
                    event_titles.append(None)

                try:
                    event_url = event_card.find("a", class_="url")['href']
                    if event_url:
                        event_bas_url.append(base + event_url)
                    else:
                        event_bas_url.append(None)
                except:
                    event_bas_url.append(None)

                banners = event_card.find("ul", class_="ds-listing-banners")
                if banners:
                    banner_list = banners.findAll('li', class_="ds-listing-series")
                    flag = False
                    for banner in banner_list:
                        if flag:
                            break
                        spans = banner.findAll("span")
                        for span in spans:
                            if "Through" in span.text:
                                flag = True
                                event_thru.append(span.text)
                                break
                else:
                    event_thru.append(None)

                cover_img = event_card.find("div", class_="ds-cover-image")
                img_url = None
                if cover_img:
                    style = cover_img.get('style')
                    if style:
                        start_index = style.find('url(') + 4
                        end_index = style.find(')')
                        img_url = style[start_index:end_index]
                event_imgs.append(img_url)
                try:
                    loc_addr = event_card.find('meta', itemprop='streetAddress').get('content').strip()

                    if loc_addr:
                        event_locs.append(loc_addr)
                    else:
                        event_locs.append(None)
                except:
                    event_locs.append(None)


                try:
                    time_element = event_card.find('div', class_='ds-event-time')
                    time = time_element.get_text(strip=True)
                    if time:
                        event_times.append(time)
                    else:
                        event_times.append(None)
                except:
                    event_times.append(None)


            print(f"page {i} done")
        else:
            print(f"Failed : {response.status_code}")
            break

    return {
        'event_titles': event_titles,
        'event_imgs': event_imgs,
        'event_locs': event_locs,
        'event_times': event_times,
        'event_BAS_urls' : event_bas_url,
        'event_thru' : event_thru
    }

print(events('http://sf-events.brokeassstuart.com/events/2024/04/15', "?page=", "http://sf-events.brokeassstuart.com"))
