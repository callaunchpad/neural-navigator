from bs4 import BeautifulSoup
import requests
import pandas as pd

def events(url, prefix):
    event_titles = []
    event_imgs = []
    event_locs = []
    event_times = []
    event_descs = [] # TODO (each event has an associated page where desc is held)
    event_purchase_url = [] # TODO

    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        event_cards = soup.find_all("div", class_="event-card")

        for event_card in event_cards:
            title = event_card.find("span", class_="ds-listing-event-title-text")
            if title:
                event_titles.append(title.get_text())
            else:
                event_titles.append(None)

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
    else:
        print(f"Failed : {response.status_code}")

    return event_titles, event_imgs, event_locs, event_times

print(events('http://sf-events.brokeassstuart.com/events/2024/04/15', None))