#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import scrython

Sets = ["IKO", "THB", "ELD", "M20", "WAR", "RNA", "GRN", "M19", "DOM", "RIX", "XLN", "HOU", "AKH", "AER", "KLD", "EMN", "SOI", "OGW", "BFZ", "ORI", "DTK", "FRF", "KTK"]
Base_URL = "https://aetherhub.com/Apps/LimitedRatings?set="

ratings_conn = sqlite3.connect('LimitedSetRatings.db')
ratings_cursor = ratings_conn.cursor()

printings_conn = sqlite3.connect('AllPrintings.sqlite')
printings_cursor = printings_conn.cursor()

for Set_ID in Sets:
    URL = Base_URL + Set_ID
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')
    table_body = soup.find(id='table_card_rating')
    rows = table_body.find_all('tr')

    for row in rows:
        cardname = row.find('a', class_="cardLink")
        if cardname is None:
            # Row didn't have card details, skip to next row
            continue

        ## Cleanup // Rated Cards
        # The number to the right of the forward slashes seems the more conditional so it's dropped for simplicity
        # Might revisit at somepoint. 
        fullstring = cardname['data-rating']
        substring = "//"
        if substring in fullstring:
            splitstring = fullstring.split('//')[0]
        else:
            splitstring = fullstring
        
        printings_cursor.execute("SELECT scryfallId FROM main.cards WHERE number = %s AND setCode = %s" % ("'{}'".format(cardname['data-number']), "'{}'".format(cardname['data-set'])))
        scryfall_id = printings_cursor.fetchone()
        
        if scryfall_id is None:
            # Try the search without the cardside
            # Cut off the Side Numbers if they exist.
            collector_number = re.findall('\d+|\D+',cardname['data-number'])[0]
            printings_cursor.execute("SELECT scryfallId FROM main.cards WHERE number = %s AND setCode = %s" % ("'{}'".format(collector_number), "'{}'".format(cardname['data-set'])))
            scryfall_id = printings_cursor.fetchone()
            
            if scryfall_id is None:
                # Still couldn't find it, fall back to scryfall API
                try:
                    # Try to get the card detail via a collector number and set search, doesn't work if set name isn't lowercase
                    card = scrython.cards.Collector(code=str(cardname['data-set']).lower(), collector_number=cardname['data-number'])
                    scryfall_id = card.id()
                except:
                    # Couldn't find it via collector number, use a fuzzy name and set search.
                    try:
                        card = scrython.cards.Named(fuzzy=cardname['data-name'],set=cardname['data-set'])
                        scryfall_id = card.id()
                    except:
                        # Couldn't find it with a fuzzy search either, skipping to next row
                        # Never hit this during testing
                        continue
            else:
                scryfall_id = scryfall_id[0]
        else:
            scryfall_id = scryfall_id[0]

        ratings_cursor.execute("INSERT INTO Main (Scryfall_id,Card_name,LSV_Rating,Set_id) VALUES(?,?,?,?)", (scryfall_id,cardname['data-name'],splitstring.strip(),cardname['data-set']))
        ratings_conn.commit()

ratings_conn.close()
printings_conn.close()
