"""Curated landmarks: a short, opinionated list of the places most people use to orient themselves
in Toronto. Not a points-of-interest database; if it isn't something a Torontonian would give
directions by, it doesn't belong here.

tier 1 = spread-out, city-scale anchors (icons from zoom 11); tier 2 = dense or local places (icons from zoom 13),
so downtown doesn't pile up when zoomed out.
aliases = other names people type into search (old names, nicknames, abbreviations).
Universities, colleges, hospitals and skyscrapers have their own toggles under Landmarks, so campuses
aren't listed here (their search nicknames live on the Universities layer in city.json). A tower that's
a sight in its own right (an observation deck, a household name) stays here as well.
Positions were checked against OpenStreetMap (Nominatim); big parks use a point inside the Toronto part.
Output: docs/toronto/data/landmarks.geojson
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'docs', 'toronto', 'data', 'landmarks.geojson')

# (name, category, tier, lat, lon, aliases)
LANDMARKS = [
    # Sports
    ('Scotiabank Arena', 'sports', 2, 43.6435, -79.3791, ['Air Canada Centre', 'ACC', 'Leafs', 'Raptors']),
    ('Rogers Centre', 'sports', 2, 43.6414, -79.3894, ['SkyDome', 'Blue Jays']),
    ('BMO Field', 'sports', 2, 43.6332, -79.4186, ['TFC', 'Argos', 'Toronto FC']),
    ('Coca-Cola Coliseum', 'sports', 2, 43.6356, -79.4148, ['Ricoh Coliseum', 'Marlies']),

    # Parks and waterfront
    ('High Park', 'park', 1, 43.6465, -79.4637, []),
    ('Trinity Bellwoods Park', 'park', 2, 43.6470, -79.4135, ['Trinity Bellwoods']),
    ('Christie Pits', 'park', 2, 43.6672, -79.4235, ['Christie Pits Park']),
    ('Riverdale Park East', 'park', 2, 43.6702, -79.3550, ['Riverdale Park']),
    ('Toronto Island Park', 'park', 1, 43.6202, -79.3678, ['Centre Island', 'Toronto Islands', 'Island']),
    ('Evergreen Brick Works', 'park', 2, 43.6845, -79.3650, ['Brick Works']),
    ('Tommy Thompson Park', 'park', 2, 43.629, -79.335, ['Leslie Street Spit', 'Leslie Spit']),
    ('Woodbine Beach', 'park', 2, 43.6627, -79.3080, ['Ashbridges Bay']),
    ("Bluffer's Park", 'park', 1, 43.7081, -79.2394, ['Scarborough Bluffs', 'Bluffers Park']),
    ('Rouge National Urban Park', 'park', 1, 43.8100, -79.1650, ['Rouge Park', 'Rouge']),

    # Live music and performance
    ('Massey Hall', 'music', 2, 43.6542, -79.3790, []),
    ('Roy Thomson Hall', 'music', 2, 43.6467, -79.3863, ['RTH']),
    ('Meridian Hall', 'music', 2, 43.6467, -79.3760, ['Sony Centre', 'Hummingbird Centre', "O'Keefe Centre"]),
    ('Budweiser Stage', 'music', 2, 43.6293, -79.4155, ['Molson Amphitheatre', 'Molson Canadian Amphitheatre']),
    ('Danforth Music Hall', 'music', 2, 43.6763, -79.3571, ['The Danforth Music Hall']),
    ('Horseshoe Tavern', 'music', 2, 43.6491, -79.3955, ['The Horseshoe', 'Horseshoe']),
    ("Lee's Palace", 'music', 2, 43.6646, -79.4093, ['Lees Palace']),
    ('History', 'music', 2, 43.6667, -79.3133, ['History Toronto', 'History venue']),

    # Government and civic
    ('City Hall & Nathan Phillips Square', 'civic', 2, 43.6530, -79.3838,
     ['Toronto City Hall', 'City Hall', 'Nathan Phillips Square', 'NPS', 'Toronto sign']),
    ("Queen's Park", 'civic', 2, 43.6625, -79.3916, ['Ontario Legislature', 'Legislative Building', 'Queens Park']),
    ('Union Station', 'civic', 2, 43.6453, -79.3806, ['Union']),


    # Culture and attractions
    ('CN Tower', 'culture', 1, 43.6426, -79.3871, []),
    ('Exhibition Place', 'culture', 1, 43.6334, -79.4120, ['CNE', 'The Ex', 'Canadian National Exhibition', 'Enercare Centre']),
    ('Royal Ontario Museum', 'culture', 2, 43.6677, -79.3948, ['ROM']),
    ('Art Gallery of Ontario', 'culture', 2, 43.6536, -79.3925, ['AGO']),
    ('St. Lawrence Market', 'culture', 2, 43.6487, -79.3716, ['St Lawrence Market']),
    ('CF Toronto Eaton Centre', 'culture', 2, 43.6544, -79.3807, ['Eaton Centre', 'Eaton Center', 'Eatons']),
    ('Toronto Zoo', 'culture', 1, 43.8196, -79.1845, ['Zoo']),

    # Airports
    ('Billy Bishop Airport', 'airport', 1, 43.6281, -79.398, ['Island Airport', 'Toronto City Airport', 'YTZ']),
    ('Pearson Airport', 'airport', 1, 43.6782, -79.6288, ['Toronto Pearson', 'YYZ', 'Pearson International']),
]

CATS = {'sports': 'Sports venue', 'park': 'Park', 'music': 'Live music', 'civic': 'Civic',
        'campus': 'Campus', 'culture': 'Culture', 'airport': 'Airport'}

feats = [{'type': 'Feature',
          'properties': {'name': n, 'cat': c, 'catLabel': CATS[c], 'tier': t, 'aliases': a},
          'geometry': {'type': 'Point', 'coordinates': [lon, lat]}}
         for n, c, t, lat, lon, a in LANDMARKS]
if __name__ == '__main__':
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(OUT, 'w'), separators=(',', ':'), ensure_ascii=False)
    print('landmarks:', len(feats))
