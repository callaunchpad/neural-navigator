from flask import Flask, flash, redirect, render_template, request, session, send_file, jsonify
import pandas as pd
from cmfrec import CMF_implicit
from datetime import datetime
from math import radians, cos, sin, asin, sqrt
import ast
import random



app = Flask(__name__)

interaction = pd.read_csv("interaction.csv")
content = pd.read_csv("events_and_locations.csv")

USER_ID = 1

berkeley_latlon = [37.8715, -122.2730]
sanjose_latlon = [37.3387, -121.8853]
sanfrancisco_latlon = [37.7749, -122.4194]
oakland_latlon = [37.8044, -122.2712]

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    km = 6371* c
    return km

class CMF_recommender:
    def __init__(self, k=40):
        self.model = CMF_implicit(
            k=k,
            random_state=1,
        )

    def fit(self, data: pd.DataFrame):
        data = data.copy()

        data = data.rename(columns={
            "user_id": "UserId",
            "item_id": "ItemId",
            "rating_id": "Rating"
        })

        self.model.fit(data)

    def recommend(self, user_id, n):
        recommendations = self.model.topN(user_id, n=n)
        return recommendations

activity_mf = CMF_recommender(k=30)
activity_mf.fit(interaction)

activity_lgcn = CMF_recommender(k=100)
activity_lgcn.fit(interaction)

@app.route('/')
def main_menu():

    day_select = request.args.get('day', type = str)
    area_select = request.args.get('area', type = str)
    radius_select = request.args.get('rad', type = int)
    tf_itin_select = request.args.get('tf_itin', type = str)
    rec_sys_select = request.args.get('rec_sys', type = str)

    # get date format
    dow_label = datetime.now().strftime('%A').lower()
    dom = str(datetime.now().day)
    month = datetime.now().strftime('%B').lower()
    final_calendar = dow_label + ", " + dom + " " + month

    # get recommendations
    if rec_sys_select == "LightGCN":
        recommendations = activity_lgcn.recommend(USER_ID, 300)
    elif rec_sys_select == "MF":
        recommendations = activity_mf.recommend(USER_ID, 300)
    else:                                                       # Implement CBF
        recommendations = activity_mf.recommend(USER_ID, 300)

    first_40 = recommendations[:25]

    random.shuffle(first_40)
    recommendations[:25] = first_40

    final_recs = []
    for i in recommendations:
        
        current_rec_id = i.copy()
        if len(final_recs) < 10:
            recommended_content = content.iloc[i]

            # check datetime format
            filter_by_day = datetime.now().strftime("%d-%m-%Y")

            if day_select:
                    date_obj = datetime.strptime(day_select, "%Y-%m-%d")

                    dow_label = date_obj.strftime('%A').lower()
                    dom = str(date_obj.day)
                    month = date_obj.strftime('%B').lower()
                    
                    final_calendar = dow_label + ", " + dom + " " + month

                    new_date_str = date_obj.strftime("%d-%m-%Y")
                    filter_by_day = new_date_str
            
            if type(recommended_content["date"]) == str:
                date_options = ast.literal_eval(recommended_content["date"])
                if filter_by_day not in date_options:
                    print("failed for day", filter_by_day)
                    continue

            # PASSED -- submitting item for display
            # type check time
            time = "Anytime"
            if type(recommended_content["time"]) == str:
                time = recommended_content["time"]
            elif type(recommended_content[dow_label]) == str:
                time = str(recommended_content[dow_label])
                if time == "Closed":
                    continue

            # type check title
            title = recommended_content["title"]
            if len(title) >= 40:
                sum_tokens = 0
                final_title = ""
                title_tokens = title.split(" ")
                for i in title_tokens:
                    if sum_tokens + len(i) < 40:
                        final_title += i + " "
                    sum_tokens += len(i) + 1
                title = final_title

            # fix distance
            current_location = [37.8756, -122.2588]
            if area_select == "Berkeley":
                current_location = berkeley_latlon
            elif area_select == "San Jose":
                current_location = sanjose_latlon
            elif area_select == "San Francisco":
                current_location = sanfrancisco_latlon
            elif area_select == "Oakland":
                current_location = oakland_latlon

            rec_lat = float(recommended_content["latitude"])
            rec_lon = float(recommended_content["longitude"])
            
            distance_from_point = int(haversine(current_location[1], current_location[0], rec_lon, rec_lat))

            if radius_select and distance_from_point > radius_select:
                continue

            distance = str(int(haversine(current_location[1], current_location[0], rec_lon, rec_lat))) + " km"

            # type check address
            address = recommended_content["address"]
            if "torino" in address.lower():
                address = "Check website"
                distance = "---"
            if len(address) >= 50:
                sum_tokens = 0
                final_address = ""
                address_tokens = address.split(", ")
                for i in address_tokens:
                    if sum_tokens + len(i) < 50:
                        final_address += i + ", "
                    sum_tokens += len(i) + 2
                address = final_address

            new_recommendation = {"title": title, "address": address, "hours": time, "distance": distance, "category": recommended_content["category"], "link": recommended_content["link"], "id": current_rec_id}
            final_recs.append(new_recommendation)
        else:
            break

    return render_template("web-interface.html", recommendations=final_recs, date_selection=final_calendar)

@app.route('/submitrating', methods=['POST'])
def submit_rating():
    if request.is_json:
        global interaction
        data = request.get_json()
        data_formatted = [
            {'item_id': data['item_id'], 'user_id': data['user_id'], 'rating_id': data['rating_id']},
        ]
        new_interaction = pd.DataFrame(data_formatted)

        interaction = pd.concat([interaction, new_interaction], ignore_index=True)
        interaction = interaction.drop_duplicates(subset=['item_id', 'user_id'], keep='last')
        interaction = interaction.drop(columns=["Unnamed: 0"])
        interaction.to_csv("interaction.csv")

        # refit model
        activity_mf.fit(interaction)
        activity_lgcn.fit(interaction)

        return jsonify(success=True)
    else:
        return jsonify({"error": "Request must be JSON"}), 400