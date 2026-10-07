"""Curated landmarks: a short, opinionated list of the places most people use to orient themselves
in Chicago. Not a points-of-interest database; if it isn't something a Chicagoan would give
directions by, it doesn't belong here.

tier 1 = spread-out, city-scale anchors (icons from zoom 11); tier 2 = dense or local places (icons from zoom 13),
so downtown doesn't pile up when zoomed out.
aliases = other names people type into search (old names, nicknames, abbreviations).
Positions were checked against OpenStreetMap (Nominatim); see raw/landmark_check.json.
Output: docs/chicago/data/landmarks.geojson
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'docs', 'chicago', 'data', 'landmarks.geojson')

# (name, category, tier, lat, lon, aliases)
LANDMARKS = [
    # Sports
    ('Wrigley Field', 'sports', 2, 41.9484, -87.6553, ['Cubs', 'Friendly Confines']),
    ('Rate Field', 'sports', 2, 41.8299, -87.6338, ['Guaranteed Rate Field', 'U.S. Cellular Field', 'Comiskey Park', 'White Sox', 'Sox Park']),
    ('United Center', 'sports', 2, 41.8807, -87.6742, ['Bulls', 'Blackhawks', 'UC']),
    ('Soldier Field', 'sports', 2, 41.8623, -87.6167, ['Bears']),

    # Parks and lakefront
    ('Millennium Park', 'park', 2, 41.8826, -87.6226, ['The Bean', 'Cloud Gate', 'Pritzker Pavilion']),
    ('Grant Park', 'park', 1, 41.8735, -87.6198, ['Buckingham Fountain']),
    ('Lincoln Park Zoo', 'park', 2, 41.9211, -87.6340, []),
    ('North Avenue Beach', 'park', 2, 41.9145, -87.6247, []),
    ('Montrose Beach', 'park', 2, 41.9653, -87.6378, ['Montrose Harbor', 'Magic Hedge']),
    ('The 606', 'park', 2, 41.9138, -87.6800, ['Bloomingdale Trail']),
    ('Garfield Park Conservatory', 'park', 2, 41.8863, -87.7173, []),
    ('Jackson Park', 'park', 1, 41.7816, -87.5807, ['Wooded Island', 'Garden of the Phoenix']),
    ('Northerly Island', 'park', 2, 41.8580, -87.6080, []),

    # Live music and performance
    ('Chicago Theatre', 'music', 2, 41.8855, -87.6274, []),
    ('Symphony Center', 'music', 2, 41.8794, -87.6248, ['Orchestra Hall', 'CSO']),
    ('Lyric Opera House', 'music', 2, 41.8826, -87.6375, ['Civic Opera House', 'Lyric Opera']),
    ('Auditorium Theatre', 'music', 2, 41.8761, -87.6253, []),
    ('Metro', 'music', 2, 41.9496, -87.6588, ['Smart Bar', 'Metro Chicago']),
    ('Aragon Ballroom', 'music', 2, 41.9692, -87.6578, ['Byline Bank Aragon Ballroom']),

    # Civic and transport
    ('City Hall', 'civic', 2, 41.8836, -87.6320, ['Chicago City Hall', 'County Building']),
    ('Union Station', 'civic', 2, 41.8786, -87.6403, ['Chicago Union Station', 'Amtrak']),
    ('Ogilvie Transportation Center', 'civic', 2, 41.8829, -87.6409, ['Ogilvie', 'Northwestern Station']),
    ('McCormick Place', 'civic', 2, 41.8517, -87.6155, []),

    # Campuses
    ('University of Chicago', 'campus', 1, 41.7900, -87.5995, ['UChicago', 'U of C']),
    ('University of Illinois Chicago', 'campus', 1, 41.8749, -87.6520, ['UIC']),
    ('Loyola University', 'campus', 2, 41.9990, -87.6578, ['Loyola University Chicago', 'Loyola']),
    ('DePaul University', 'campus', 2, 41.9246, -87.6507, ['DePaul']),
    ('Northwestern (Chicago campus)', 'campus', 2, 41.8960, -87.6185, ['Northwestern Memorial', 'Feinberg', 'Northwestern']),
    ('Illinois Tech', 'campus', 2, 41.8349, -87.6270, ['IIT', 'Illinois Institute of Technology']),

    # Museums and sights
    ('Art Institute', 'culture', 2, 41.8796, -87.6237, ['Art Institute of Chicago', 'AIC']),
    ('Field Museum', 'culture', 2, 41.8663, -87.6170, []),
    ('Shedd Aquarium', 'culture', 2, 41.8676, -87.6140, ['Shedd']),
    ('Adler Planetarium', 'culture', 2, 41.8663, -87.6068, ['Adler']),
    ('Museum of Science and Industry', 'culture', 2, 41.7906, -87.5831, ['MSI']),
    ('Navy Pier', 'culture', 2, 41.8917, -87.6086, []),
    ('Willis Tower', 'culture', 2, 41.8789, -87.6359, ['Sears Tower', 'Skydeck']),
    ('875 North Michigan', 'culture', 2, 41.8988, -87.6229, ['John Hancock Center', 'Hancock']),
    ('Merchandise Mart', 'culture', 2, 41.8885, -87.6354, ['The Mart']),

    # Airports
    ("O'Hare Airport", 'airport', 1, 41.9800, -87.9098, ["O'Hare International Airport", 'ORD', 'OHare']),
    ('Midway Airport', 'airport', 1, 41.7868, -87.7522, ['Midway International Airport', 'MDW']),
]

CAT_LABEL = {'sports': 'Sports venue', 'park': 'Park and lakefront', 'music': 'Music and theatre', 'civic': 'Civic and transport',
             'campus': 'Campus', 'culture': 'Museum or sight', 'airport': 'Airport'}

if __name__ == '__main__':
    feats = [{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
              'properties': {'name': n, 'cat': c, 'catLabel': CAT_LABEL[c], 'tier': t, 'aliases': a}}
             for n, c, t, lat, lon, a in LANDMARKS]
    json.dump({'type': 'FeatureCollection', 'features': feats}, open(OUT, 'w'), separators=(',', ':'))
    print('landmarks:', len(feats))
