"""Chicago's hand-kept lists: community area names, the nine sides, and known-as names.

Sides: the conventional split of Chicago's 77 community areas into nine "sides" (Far North,
Northwest, North, West, Central, South, Southwest, Far Southwest and Far Southeast). It is an
informal convention, not an official boundary, but it is how Chicagoans place a neighbourhood.

Known-as names: the City's Neighborhoods layer (98 areas, 2012) already names the places people
call neighbourhoods that aren't community areas (Wicker Park, Gold Coast, Pilsen's neighbours...).
Those come from the data; KNOWN_AS_EXTRA adds a few common names it lacks. Points are approximate
centres (lon, lat), checked against OpenStreetMap. kind: district | enclave | village
"""

FIX = {'Mckinley Park': 'McKinley Park', "O'hare": "O'Hare", 'Ohare': "O'Hare", 'Lakeview': 'Lake View'}


def ca_name(s):
    t = s.title().replace("'S", "'s")
    return FIX.get(t, t)


SIDES = {
    'Far North Side': [1, 2, 3, 4, 9, 10, 11, 12, 13, 14, 76, 77],
    'Northwest Side': [15, 16, 17, 18, 19, 20],
    'North Side': [5, 6, 7, 21, 22],
    'Central': [8, 32, 33],
    'West Side': [23, 24, 25, 26, 27, 28, 29, 30, 31],
    'South Side': [34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 60, 69],
    'Southwest Side': [56, 57, 58, 59, 61, 62, 63, 64, 65, 66, 67, 68],
    'Far Southwest Side': [70, 71, 72, 73, 74, 75],
    'Far Southeast Side': [44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55],
}
SIDE_INFO = {
    'Far North Side': "From Rogers Park and Edgewater on the lake out to O'Hare.",
    'Northwest Side': 'Bungalow belt neighbourhoods around Portage Park and Belmont Cragin.',
    'North Side': 'Lake View, Lincoln Park, Logan Square and their neighbours.',
    'Central': 'The Loop, the Near North Side and the Near South Side.',
    'West Side': 'From West Town and the Near West Side out to Austin.',
    'South Side': 'Bridgeport, Bronzeville, Hyde Park, Woodlawn and South Shore.',
    'Southwest Side': 'From McKinley Park and Brighton Park down to Englewood and Midway.',
    'Far Southwest Side': 'Beverly, Mount Greenwood, Morgan Park and their neighbours.',
    'Far Southeast Side': 'Chatham to Hegewisch, including Pullman and the Calumet area.',
}
assert sorted(n for v in SIDES.values() for n in v) == list(range(1, 78))

# Names from the City's Neighborhoods layer: keep as is, rename, or drop (parks, campuses, venues,
# and names that only repeat a community area).
KNOWN_AS_RENAME = {'Little Italy, UIC': 'Little Italy', 'Sauganash,Forest Glen': 'Sauganash', 'Boystown': 'Northalsted'}
KNOWN_AS_DROP = {'Grant Park', 'Jackson Park', 'Millenium Park', 'Museum Campus', "O'Hare", 'United Center',
                 'Garfield Park', 'Grand Crossing', 'Sheffield & DePaul'}
ENCLAVES = {'Chinatown', 'Greektown', 'Little Italy', 'Little Village', 'Ukrainian Village', 'Pilsen', 'Andersonville'}
VILLAGES = {'Northalsted'}

KNOWN_AS_EXTRA = [
    ('Pilsen', -87.6600, 41.8560),
    ('Bronzeville', -87.6170, 41.8250),
    ('South Loop', -87.6258, 41.8658),
    ('Fulton Market', -87.6481, 41.8869),
    ('River West', -87.6530, 41.8935),
    ('Roscoe Village', -87.6800, 41.9430),
    ('Ravenswood', -87.6792, 41.9688),
    ('Back of the Yards', -87.6649, 41.8048),
    ('Canaryville', -87.6420, 41.8155),
    ('Old Irving Park', -87.7350, 41.9545),
]


def known_as_kind(name):
    return 'enclave' if name in ENCLAVES else 'village' if name in VILLAGES else 'district'


# Street names as Chicagoans write them: no leading direction, short suffix ("West North Avenue" -> "North Ave").
DIRS = {'North', 'South', 'East', 'West', 'N', 'S', 'E', 'W'}
SUFFIX = {'Avenue': 'Ave', 'Street': 'St', 'Road': 'Rd', 'Boulevard': 'Blvd', 'Drive': 'Dr', 'Parkway': 'Pkwy',
          'Highway': 'Hwy', 'Place': 'Pl', 'Court': 'Ct', 'Lane': 'Ln', 'Terrace': 'Ter'}


def street_name(s):
    w = s.replace('Martin Luther King Junior', 'Martin Luther King Jr').split()
    if len(w) > 2 and w[0] in DIRS:
        w = w[1:]
    if w and w[-1] in SUFFIX:
        w[-1] = SUFFIX[w[-1]]
    return ' '.join(w)


# The streets people navigate by: the mile-grid arterials, the diagonals and the boulevards along the lake.
# Everything else OpenStreetMap tags primary or secondary inside the city is drawn as a minor street.
MAJOR_STREETS = {
    # east-west, north to south
    'Howard St', 'Touhy Ave', 'Devon Ave', 'Peterson Ave', 'Foster Ave', 'Lawrence Ave', 'Montrose Ave', 'Irving Park Rd',
    'Addison St', 'Belmont Ave', 'Diversey Ave', 'Diversey Pkwy', 'Fullerton Ave', 'Armitage Ave', 'North Ave', 'Division St',
    'Chicago Ave', 'Grand Ave', 'Lake St', 'Madison St', 'Roosevelt Rd', 'Cermak Rd', '31st St', 'Pershing Rd',
    '47th St', '55th St', 'Garfield Blvd', '63rd St', '71st St', '79th St', '87th St', '95th St', '103rd St',
    '111th St', '119th St', '127th St', '130th St', '138th St',
    # north-south, east to west
    'Lake Shore Dr', 'DuSable Lake Shore Dr', 'Sheridan Rd', 'Michigan Ave', 'State St', 'Halsted St', 'Ashland Ave',
    'Western Ave', 'California Ave', 'Kedzie Ave', 'Pulaski Rd', 'Cicero Ave', 'Central Ave', 'Austin Ave', 'Harlem Ave',
    'Cumberland Ave', 'Stony Island Ave', 'Cottage Grove Ave', 'Martin Luther King Dr', 'Torrence Ave',
    # diagonals
    'Milwaukee Ave', 'Elston Ave', 'Lincoln Ave', 'Clark St', 'Broadway', 'Ogden Ave', 'Archer Ave', 'Vincennes Ave',
    'Northwest Hwy', 'South Chicago Ave', 'Ridge Ave',
}

# SSA names as the City's file abbreviates them, written out.
SSA_NAMES = {'CentLakeview/Wrigleyville': 'Central Lakeview/Wrigleyville', 'Greek Town': 'Greektown',
             'West Town-2014': 'West Town', 'Calumet Hts/Avalon': 'Calumet Heights/Avalon',
             'Village:AustinChgoAvCCorr': 'Austin / Chicago Avenue', 'Andersonville-Clark St': 'Andersonville',
             'Lincoln Park/Clark St': 'Lincoln Park', 'Clark St (Rogers Park)': 'Rogers Park', 'Devon Ave': 'Devon Avenue',
             'Sheridan Rd': 'Sheridan Road', '87th St Business Corridor': '87th Street', '71st - Stony Island': '71st/Stony Island',
             'Cottage Grove - 47th St': 'Cottage Grove/47th', 'Auburn Gresham/79th St': 'Auburn Gresham/79th Street'}
