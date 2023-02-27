import json
import base64
import pycountry
import folium
from flask import Flask, render_template, request, redirect, url_for
from requests import post, get
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

app = Flask(__name__)
CLIENT_ID='af650555f3444a9ba1c3af5ae28fa6a3'
CLIENT_SECRET='e654272fdcbf4b51b777b62b48805d32'

def get_token():
    """
    Get token out of client ID and client secret.
    """
    auth_code = f'{CLIENT_ID}:{CLIENT_SECRET}'
    auth_bytes = auth_code.encode('utf-8')
    auth_base64 = str(base64.b64encode(auth_bytes), 'utf-8')
    auth_url = 'https://accounts.spotify.com/api/token'
    auth_data = {'grant_type': 'client_credentials'}
    auth_headers = {'Authorization': 'Basic ' + auth_base64,
               'Content-Type': 'application/x-www-form-urlencoded'}
    result = post(auth_url, headers = auth_headers, data = auth_data)
    json_result = json.loads(result.content)
    token = json_result['access_token']
    return token

def get_auth_header(token):
    """
    Get authorization header.
    """
    return {'Authorization': 'Bearer ' + token}

def search_for_artist(token, artist_name):
    """
    Search for an artist`s name and ID.
    """
    artist_url = 'https://api.spotify.com/v1/search'
    artist_headers = get_auth_header(token)
    query = f'?q={artist_name}&type=artist&limit=1'
    query_url = artist_url + query
    result = get(query_url, headers = artist_headers)
    json_result = json.loads(result.content)['artists']['items']
    if len(json_result) == 0:
        print('No such artist found')
        return None
    return json_result[0]['name'], json_result[0]['id']

def get_most_popular_song(token, artist_name):
    """
    Search for a name and ID of the most popular song of an artist.
    """
    artist_id = search_for_artist(token, artist_name)[1]
    song_url = f'https://api.spotify.com/v1/artists/{artist_id}/top-tracks?country=US'
    song_headers = get_auth_header(token)
    result = get(song_url, headers = song_headers)
    json_result = json.loads(result.content)['tracks']
    return json_result[0]['name'], json_result[0]['id']

def get_track_country_list(token, artist_name):
    """
    Get a list of countries where the most popular artist`s song
    is available to listen.
    """
    track_id = get_most_popular_song(token, artist_name)[1]
    track_url = f'https://api.spotify.com/v1/tracks/{track_id}'
    track_headers = get_auth_header(token)
    result = get(track_url, headers = track_headers)
    json_result = json.loads(result.content)
    country_list = json_result['available_markets']
    new_country_list = []
    for country in country_list:
        country = pycountry.countries.get(alpha_2=country)
        if country is None:
            continue
        if ',' in country.name:
            country_name = country.name.split(',')[0]

        else:
            country_name = country.name
        new_country_list.append(country_name)
    return new_country_list

def create_country_map(artist_name):
    """
    Create a map with countries where it is available to listen
    the most popular song of an artist.
    """
    token = get_token()
    artist_name = search_for_artist(token, artist_name)[0]
    track_name = get_most_popular_song(token, artist_name)[0]
    country_list = get_track_country_list(token, artist_name)
    geolocator = Nominatim(user_agent="https://www.openstreetmap.org/copyright")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    map = folium.Map(location=[49.83826, 24.02324], zoom_start=10)
    country_loc = folium.FeatureGroup(name="Country")
    for country in country_list:
        location = geolocator.geocode(country)
        country_loc.add_child(folium.Marker(location=[location.latitude, location.longitude],
                    popup = folium.Popup(f'<h1><strong>{country}</strong></h1> "{track_name}" by {artist_name}', max_width = 200, min_width = 200),
                    icon=folium.Icon(icon="fa-music", prefix='fa', color = "purple")))
    map.add_child(country_loc)
    return map._repr_html_()

@app.route('/', methods=['POST', 'GET'])
def get_info():
    if request.method == 'POST':
        user = request.form['q']
        return redirect(url_for('user', usr = user))
    else:
        return render_template('button.html')

@app.route('/<usr>')
def user(usr):
    artist = f'{usr}'
    return create_country_map(artist)

if __name__ == '__main__':
    app.run(debug=True)