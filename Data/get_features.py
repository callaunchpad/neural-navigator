import pandas as pd
from tqdm import tqdm

# Idea 2: get review descriptor aggregations
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

driver = webdriver.Chrome()

def get_keywords(url, attempts):

    try:
        driver.get(url)
    except:
        return get_keywords(url, attempts + 1)
    
    kw = {}
    all_buttons = driver.find_elements(By.CSS_SELECTOR, "button")
    
    for button in all_buttons:
        aria_label = button.get_attribute("aria-label")
        if aria_label and ", mentioned in" in aria_label:
            cat_label = aria_label.split(",")[0]
            ct_label = int(aria_label.split(",")[1].replace("mentioned in ", "").replace(" reviews", ""))
            kw[cat_label] = ct_label
            
    ###### REPEAT
    if len(kw) == 0: 
        if attempts != 5: # If single failure, so far has always had it on second so should be good
            return get_keywords(url, attempts + 1)
    ######
    
    return kw


subset_short = pd.read_csv("final_savepoint.csv")

# Iterate feature extraction full bay
failed = []

START_INDEX = 900
END_INDEX = 910

for index, row in tqdm(subset_short.iloc[START_INDEX:END_INDEX,:].iterrows()):
    if type(row['link']) == str:
        try:
            features = get_keywords(row['link'], 0)
            subset_short.loc[subset_short.index == index, 'features'] = [features]
        except:
            print("failed!")
            failed.append(row['title'])
    else:
        print("no link!")
    if index % 10 == 0:
        subset_short.to_csv('{}_savepoint.csv'.format(index), index=True)
print(failed)

subset_short.to_csv('final_savepoint.csv'.format(index), index=True)