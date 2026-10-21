"""
Scam-score regression tests (scam.py). See SCAM_FILTER.md.

No pytest dependency — run directly:

    .venv/bin/python test_scam.py

CONFIRMED  scams whose poster answered with a scam script (October 2026)
JUDGED     scams judged from the ad itself (template swaps, contact harvesting, …)
LEGIT      real posts that must stay clean, chosen to sit near the rules' edges

All are real Craigslist posts (contact details and street addresses redacted).
Posts already removed keep the first 300 characters the agent had cached; their
titles and locations were reconstructed from the URL. Every flagged case must
score >= config.SCAM_FLAG_SCORE and every legit one below it.

A scam got through? Add it to CONFIRMED or JUDGED first, then adjust a weight
or regex in scam.py until it's flagged and every LEGIT case stays clean.
"""

import config
import scam
from filter import _assign_region, filter_listings
from models import Listing

_n = 0


def _cl(why: str, **fields) -> Listing:
    global _n
    _n += 1
    return Listing(id=f"case{_n}", source="craigslist_nyc", url=f"https://example.com/{_n}",
                   body_snippet=fields.get("body", "")[:300], **fields), why


CONFIRMED = [
    _cl(  # m3brJPR1D8RKmNew2sTY6w (live)
        why="LES studio $1,300: 'next to 1,2,3 trains', a template reused for Cobble Hill",
        title="Spacious Sublet in Lower East Side. Oct to May (maybe longer)",
        price=1300,
        bedrooms=0,
        category="sublets",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["2", "laundry in bldg"], "parking": ["5", "street parking"], "ev_charging": ["1", "ev charging"]},
        body="A furnished sublet is available in a studio/1 bath in the LES neighborhood of "
              "Manhattan, next to 1,2,3 trains. Move in date can be mid October if needed. And the "
              "apartment is available until the 30th of April if needed as well. The rent for one "
              "month is $1,300. All utilities are included. Please tell me about yourself and the "
              "details of your desired sublet when you respond to the ad. Thanks!",
    ),
    _cl(  # j4vMCyYHB94CSEqoZGRC1r (live)
        why="East Village 'luxury condo' 1BR $1,650: copy lifted from a ~$5,750 listing",
        title="Spacious Quiet 1BR Condo | Doorman, Gym, Roof Deck | East Village",
        price=1650,
        bedrooms=1,
        category="sublets",
        attrs={"laundry": ["1", "w/d in unit"], "parking": ["2", "attached garage"]},
        body="Spacious north-facing 1-bedroom apartment in a full-service luxury condominium located "
              "in the heart of the East Village. This quiet residence faces away from the street and "
              "features hardwood floors, approximately 10-foot ceilings, central heating and air "
              "conditioning, and oversized double-pane windows that provide excellent natural light. "
              "Motorized window shades offer added privacy. The open kitchen is equipped with premium "
              "appliances, including a Sub-Zero refrigerator and wine cooler, Bosch dishwasher, and "
              "Wolf gas range—ideal for everyday living and entertaining. Apartment Features: Spacious "
              "1-bedroom layout Hardwood flooring High ceilings Central heating & air conditioning "
              "Large double-pane windows Quiet courtyard-facing exposure Motorized window shades Open "
              "chef's kitchen Premium stainless steel appliances Excellent natural light Building "
              "Amenities: 24-hour doorman/concierge Fitness center with premium equipment Resident "
              "lounge with seating, TV, and pool table Landscaped rooftop terrace with grill and "
              "outdoor seating Elevator building High-speed Wi-Fi in common amenity spaces Pri",
    ),
    _cl(  # g1EbbXNNWnrA3m4QufTLp1 (live)
        why="Williamsburg garden 1BR $1,450: vacation-rental copy; replied from Gmail asking $2,650 "
             "up front",
        title="A 1bedroom apartment with garden in Williamsburg",
        price=1450,
        category="sublets",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["1", "w/d in unit"], "parking": ["4", "off-street parking"], "wheelchaccess": ["1", "wheelchair accessible"]},
        body="1 bedroom apartment with a huge decked garden, 3 blocks from the Lorimer stop on the L "
              "and G trains. Sofa bed with an inflatable topper in the living room sleeps another 2. "
              "Gas BBQ, chaise lounges and outdoor seating for al fresco meals. The apartment is in a "
              "recently renovated 1890 s wood frame row house 3 blocks from the Lorimer stop on the L "
              "subway train, a 5 minute ride into Manhattan. While close to great restaurants, cafes, "
              "bars, coffee shops and super-hipster Williamsburg shopping, the house is on a very "
              "quiet, tree lined street with a garden, giving one a feeling of being in the country, "
              "just a few minutes from the heart of NYC. Both the living room and bedroom open out "
              "onto the garden. Specifics: -1 bedroom: 1 x king bed plus 1 queen sofa-bed in the "
              "living room (sleeps up to 4) -1 bathroom -full kitchen with granite counter tops, fully "
              "outfitted kitchen with stainless steel appliances; 6 burner gas stove, dishwasher, "
              "microwave, large refrigerator, toaster , and french press and Keurig coffee makers. "
              "Kitchen generally stocked with milk, butter, coffee, tea, bread, eggs, basic",
    ),
    _cl(  # 1TH4NmCiZwRzpvBq4z5jPs (live)
        why="Downtown Brooklyn studio $1,500 in a ~$4,000-studio building: 'only video tour, away on "
             "business'",
        title="Furnished Downtown Brooklyn studio, Jan 19-May 18, utilities included",
        price=1500,
        bedrooms=0,
        category="sublets",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["1", "w/d in unit"], "parking": ["2", "attached garage"], "wheelchaccess": ["1", "wheelchair accessible"]},
        body="I'm looking for someone to take over my furnished studio on [address] for the spring, "
              "January 19 through May 18, 2027 (about four months). I'll be away for those months and "
              "would rather hand the place to someone careful than leave it empty. The details: - "
              "Studio, 1 bathroom, fully furnished - $1,500 a month, all utilities included - Quiet "
              "block in the heart of the Downtown Brooklyn, close to restaurants, cafes, groceries and "
              "the subway - Landlord approval for the sublet is already in place",
    ),
    _cl(  # bnynxskKzHD1beUjPT1Fen (live)
        why="LES 1BR $1,700: one of ~10 identical posts (title reconstructed from its siblings, "
             "which swap only the area and the train lines)",
        title="1-bed 1-bath sublet mid to end Sept until.2027 sublet in Lower East",
        neighborhood="Lower East Side",
        price=1700,
        bedrooms=1,
        category="sublets",
        body="Private apartment available anytime between mid to end September - 2027 $1700 per "
              "month, which covers rent, utilities, and 1Gb internet (price negotiable for longer "
              "periods) Apartment is furnished, but includes a full kitchen with standard appliances. "
              "Great location with public transit options. (Located near all major transportation "
              "including the F, J, M, Z trains.) Note: A/C is included.",
    ),
    _cl(  # w6cxxLzdacFLhebtchMmRm (live)
        why="South Slope room $755: 'luxury high-rise' title, basic 3BR text, garage + EV tags",
        title="Sunny Bedroom in Luxury South Slope High Rise Apt",
        price=755,
        bedrooms=1,
        category="rooms",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["1", "w/d in unit"], "parking": ["2", "attached garage"], "wheelchaccess": ["1", "wheelchair accessible"], "ev_charging": ["1", "ev charging"]},
        body="I am a writer-musician (aka pet sitter) seeking a dependable roommate for a private "
              "room in a 3-bedroom South Slope apartment. The room is private, approximately 8' x 10', "
              "with a closet. The apartment itself is basic but all the appliances work and are "
              "relatively new. Heat. hot water. and water pressure are good. Wifi is fast. No rodents "
              "or roaches. I am frequently away for work, so I'll want someone I can trust to keep the "
              "place clean, but you'll regularly have the common areas to yourself. (The third room is "
              "occupied by a very quiet, non-social tenant--female, maybe 30?--who pretty much stays "
              "in her room when she’s in the apartment. Interaction is near-zero, literally have only "
              "seen her a few times this year). There is a possibility to move into her room, which is "
              "the largest, sunniest room in the apartment, hopefully soon. Location: 13th St (between "
              "4th/5th). 15 min subway to Manhattan, 15 min walk to Prospect Park. The Household "
              "Dynamic It would be great to have someone I'd want to be friends with, but being "
              "friendly when we bump into each other in the kitchen is probably good en",
    ),
    _cl(  # tvdkJWp9WrjcnkCBgyPgbu (live)
        why="East Village corner 1BR + roof deck $1,800: every amenity at half the median",
        title="Spacious 1 BR in East Village: Oct to May (maybe longer)",
        price=1800,
        bedrooms=1,
        category="sublets",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["1", "w/d in unit"], "parking": ["5", "street parking"], "ev_charging": ["1", "ev charging"]},
        body="Beautiful sun-drenched corner 1 BR with private roof deck overlooking park in the heart "
              "of the East Village near to all EV has to offer including Trader Joes, Dimes Square, "
              "Essex Market. F train is 1 block away, FMJZ is 2 blocks away, BD is a short walk.",
    ),
]

JUDGED = [
    _cl(  # jJXVwWVEZafKi7sGRPEfSr (live)
        why="SoHo 'walk-up suite' 1BR $1,500 tagged wheelchair accessible",
        title="Available Immediately",
        price=1500,
        bedrooms=1,
        category="rooms",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["2", "laundry in bldg"], "parking": ["2", "attached garage"], "wheelchaccess": ["1", "wheelchair accessible"], "ev_charging": ["1", "ev charging"]},
        body="Newly finished walk-up suite in beautiful, quiet location Sunny and bright, 1 bedroom, "
              "separate entrance, private bathroom, washer and dryer, kitchenette. 800 sq. feet. On "
              "park with bike paths/walking paths right outside door. Furnished.",
    ),
    _cl(  # wNQXyQ1d3Za7BEv7cJkvFY (cached first 300 chars; post removed)
        why="'East Village' studio $1,350 near 72nd St (1/2/3, B/C), Central Park, Riverside Park",
        title="Spacious Studio in East Village",
        neighborhood="East Village",
        price=1350,
        body="Enjoy a quiet, fully furnished apartment close to Central Park, Riverside Park, 72nd "
              "Streetsubway (1/2/3 and B/C trains), restaurants, cafes, neighborhood shops, and "
              "cultural attractions. Oct–May 14th. Features: • Elevator building • Laundry in the "
              "building • Dishwasher • W",
    ),
    _cl(  # nS36GAtj8b2wwnPMfCmuKV (live)
        why="Brooklyn Heights room $950 'negotiable', bundled with a paid assistant job",
        title="2BR SHARE",
        price=950,
        bedrooms=2,
        category="rooms",
        attrs={"laundry": ["2", "laundry in bldg"], "parking": ["5", "street parking"]},
        body="Actress, dancer, and model is looking to share, with compatible male or female "
              "housemate, her fully-furnished 2BR apartment in Brooklyn Heights. The building: -- is "
              "mid-rise, with elevator, on a major street; -- has a live-in super, a part-time "
              "doorman, and roof deck with great views, as well as fitness and laundry rooms; and -- "
              "is near several subways (one stop to Manhattan), buses, citibikes, supermarkets, "
              "pharmacies, bars, restaurants, shopping, Brooklyn Bridge, parks, and promenade. The "
              "apartment has good heat, light, air-conditioning, and internet. The spare bedroom is "
              "fairly large with full sized bed, new mattress, dresser, closet, desk and tv. Your "
              "rent, including utilities, would be $950 a month, but very negotiable, because rent is "
              "secondary to compatibility, and am also in need of a paid assistant for my home office. "
              "Am happy to call you later today.  Meantime, please tell me all about yourself.",
    ),
    _cl(  # 93zjdeC7FqVBNSUeZa4qgU (live)
        why="Seaport studio $1,269: 'ONLY MESSAGES WITH EMAIL AND PHONE NUMBER'",
        title="Beautifully furnished Studio",
        price=1269,
        bedrooms=0,
        category="sublets",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["1", "w/d in unit"], "parking": ["2", "attached garage"], "wheelchaccess": ["1", "wheelchair accessible"], "ev_charging": ["1", "ev charging"]},
        body="BRAND NEW TO MARKET!  High floor big beautiful studio with lots of light and renovated "
              "kitchen. **Apartment can come fully furnished or unfurnished. The building has great "
              "amenities completely Free,  Gym with classes, rooftop deck, game room, lounge, multiple "
              "laundry rooms, 24 hr doorman, etc.  2-3 minutes away from the 2/3, 4/5, J/Z subway "
              "stations plus only 5 minutes away from main Fulton subway station and brand new Whole "
              "Foods around the corner and new Tin building by Seaport plus multiple coffee shops, "
              "restaurants, bars around the corner. Email me for more information. IT IS AVAILABLE TO "
              "MOVE IN NOW. FOR SWIFT RESPONSE, PLEASE SEND YOUR EMAIL AND PHONE NUMBER FOR DETAILS. "
              "ONLY MESSAGES WITH EMAIL AND PHONE NUMBER WILL BE RESPONDED TO. Don't miss this "
              "opportunity! Close to schools, public transportation, Hospitals, major highways, "
              "businesses, Restaurants, etc. \"first-come first-serve\" basis. Don't miss out!",
    ),
    _cl(  # sC68NemYx7WNdzvrySNawd (live)
        why="Williamsburg living room $1,369: same script, walk-up tagged wheelchair accessible",
        title="A nice furnished living room available",
        price=1369,
        bedrooms=1,
        category="sublets",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["1", "w/d in unit"], "parking": ["2", "attached garage"], "wheelchaccess": ["1", "wheelchair accessible"], "ev_charging": ["1", "ev charging"]},
        body="Fully furnished 1 bedroom plus home office in prime Williamsburg, steps from "
              "\"Bedford\" L train, McCarren Park, multiple restaurants, coffee shops, grocery stores, "
              "bars, and unlimited stores. **Please note this is rented fully furnished ONLY for a "
              "minimum 12 month lease. Apartment is on a 4th floor walk up so 3 flights of stairs up. "
              "This space blends convenience and comfort with a large kitchen, living room, and "
              "dedicated office space.    The apartment has great natural light and comes with a A/C "
              "mini split system. Explore the finest dining, shops, and nightlife within walking "
              "distance of the apartment! Perfect for someone in the city for a temporary stay or "
              "someone who needs an exceptional apartment between leases. The space Bedroom: "
              "Queen-size bedroom offering comfort and extensive storage. Living Room: The living room "
              "boasts an oversized L-shaped couch that transforms into a queen-size bed, providing "
              "versatility and comfort for relaxation and movie nights or for those family/friends "
              "visiting for the weekend! Kitchen: The well-equipped kitchen is designed for cooking "
              "and hosting fri",
    ),
    _cl(  # wraFki46Tjizo7Sk7Y1VxH (live)
        why="Greenpoint 1BR $1,400: 'Give us your phone number … we'll call back'",
        title="##Gorgeous 1 bedroom 1 bath apartment located in Greenpoint.##",
        price=1400,
        bedrooms=1,
        category="rooms",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["1", "w/d in unit"], "parking": ["4", "off-street parking"]},
        body="Gorgeous railroad style apartment located on the 3rd floor, top floor, with windows in "
              "every room, located on a quiet Tree lined Street. Gorgeous kitchen with cherry wood "
              "kitchen cabinets, stainless steel appliances, including dishwasher, granite counter "
              "tops and tons and tons of counterspace. Hospitals & Medical Centers: CityMD Greenpoint, "
              "NYC Health + Hospitals/Woodhull, NewYork-Presbyterian Brooklyn Methodist Hospital. "
              "Parks & Recreation: McGolrick Park, McCarren Park, American Playground, Greenpoint "
              "Public Park. Education: P.S. 34, P.S. 110 The Monitor, John Ericsson Middle School 126, "
              "A-Tech High School. Transportation: G Train at Nassau Avenue, G Train at Greenpoint "
              "Avenue, L Train at Bedford Avenue, India Street Ferry Landing. -Give us your phone "
              "number in response, and we'll give you a call back to discuss further details and set "
              "up a viewing time!",
    ),
    _cl(  # i8auedEAxdrHFePBKFWbmW (live)
        why="East Village 1BR $1,650: tagged w/d in unit, text says 'multiple laundromats nearby'",
        title="EAST VILLAGE SUBLET — KING-SIZE BEDROOM + MASSIVE LIVING SPACE — 1 FLI",
        price=1650,
        bedrooms=1,
        category="sublets",
        attrs={"laundry": ["1", "w/d in unit"], "parking": ["3", "detached garage"]},
        body="King-size bedroom area Massive living room with plenty of space for a full living room "
              "furniture set + dining table Great natural light throughout North & South exposures "
              "Open-concept kitchen Gas stove Lots of cabinet + counter space Hardwood floors Central "
              "building heat Video intercom 1 flight up AMAZING EAST VILLAGE LOCATION: 1 block from "
              "Tompkins Square Park Surrounded by tons of bars, restaurants, coffee shops, vintage "
              "stores, and neighborhood spots Multiple laundromats nearby Everything you need within "
              "easy walking distance GREAT SUBWAY ACCESS: F Train — 2nd Ave Station 6 Train — Astor "
              "Place Station L Train — 1st Ave Station Short walk to the N / R / W at 8th St Station "
              "Great East Village location with a surprisingly spacious layout, excellent natural "
              "light, and easy access to transportation, restaurants, nightlife, and everything the "
              "neighborhood has to offer.",
    ),
    _cl(  # wqTPUn6ZtkHj9brwhPWq83 (cached first 300 chars; post removed)
        why="Cobble Hill $1,700: the LES $1,300 text with the area and trains swapped",
        title="Spacious Sublet in Cobble Hill",
        neighborhood="Cobble Hill",
        price=1700,
        body="A furnished sublet is available in a studio/1 bath in the Cobble Hill neighborhood of "
              "Brooklyn, next to 2, 3, 4, 5 and R trains. Move in date can be mid October if needed. "
              "And the apartment is available until the 30th of April if needed as well. The rent for "
              "one month is $1",
    ),
    _cl(  # 2fPYTKdYPvgLzgxWCEgbt7 (cached first 300 chars; post removed)
        why="Murray Hill 1BR $1,700: the East Village studio text re-posted as a one-bedroom",
        title="Murray Hill Sublet: Oct, to Dec. 31 With Renewal Option",
        neighborhood="Murray Hill",
        price=1700,
        body="Beautiful, Clean, Modern one bed for month-month Rental. THIS IS ONLY AVAILABLE UNTIL "
              "DECEMBER 31, 2026 with renewal option. Modern Bathroom Modern Kitchen and Appliances "
              "Pied-a-terre allowed Cable TV and WIFI Electricity, Water, Hot water, and heat included",
    ),
    _cl(  # x3FWSKrvXNRRdehvPhAG3h (live)
        why="East Village studio $1,350: the Murray Hill copy's original",
        title="East Village Sublet: Oct, to Dec. 31 With Renewal Option",
        price=1350,
        bedrooms=1,
        category="sublets",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["2", "laundry in bldg"], "parking": ["5", "street parking"], "wheelchaccess": ["1", "wheelchair accessible"]},
        body="Beautiful, Clean, Modern Studio for month-month Rental. THIS IS ONLY AVAILABLE UNTIL "
              "DECEMBER 31, 2026 with renewal option. Modern Bathroom Modern Kitchen and Appliances "
              "Pied-a-terre allowed Cable TV and WIFI Electricity, Water, Hot water, and heat included",
    ),
]

LEGIT = [
    _cl(  # 8BzEDcVcGh41MktsMfR2Qx (live)
        why="Flatbush room $1,350 in a rent-stabilized building",
        title="Available Nov 15 - Large Bedroom available in 2-BDR Apt!",
        price=1350,
        bedrooms=2,
        category="rooms",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["2", "laundry in bldg"], "parking": ["2", "attached garage"]},
        body="1 or 2 Roommates to fill one LARGE bedroom in a generously sized two-bedroom apartment. "
              "Strongly considering women and LGBTQ+ identifying folx interested in a long-term "
              "sublet. Open to couples. Must be comfortable living with cats. Not able to accommodate "
              "any other animals at this time. RENT: $1350/mo, with utilities (including internet) "
              "under $70/mo  monthly. Available from November 15 to August 1 with possibility to "
              "extend time. Move in can be flexible after November 1. ROOM DETAILS: The bedroom is "
              "LARGE by New York standards, offers low light, and contains 2 large closets inside the "
              "room. Room resides closest to the bathroom is across the apartment from my room. Room "
              "can accommodate a King Size Bed with space for a desk, bookshelves and dresser. "
              "Currently unfurnished. APARTMENT:  Fully-furnished apartment with ability to "
              "accommodate kitchen appliances and tools. Large living room and entry-way able to store "
              "one bike. 2 very friendly cats who will love you! Compost and waste-friendly practices "
              "considered (but not exclusive!) Heat works in winter, air conditioner available for use "
              "i",
    ),
    _cl(  # 37xRuvUnGzdXt1RY5otqbE (live)
        why="Prospect Heights 1BR $1,200 for Nov 20-29: short stay, priced per stay",
        title="Beautiful 1-Bed Prospect Heights Brownstone, Nov 20-29",
        price=1200,
        category="sublets",
        attrs={"laundry": ["5", "no laundry on site"], "parking": ["7", "no parking"]},
        body="Please read the entire description! Subletting a light-filled one bedroom in a "
              "beautiful historic brownstone in Prospect Heights from Nov 20-29. The apartment is "
              "fully furnished and technically is a two bedroom but currently set up as a one bedroom "
              "with a separate dining room / office, kitchen, and living room (with a very comfortable "
              "West Elm futon couch that folds down if you wanted a second bed). The rent is $1200 for "
              "9 nights in this case. Preference will be given to those who can take it for the whole "
              "time. Incredible location. 10 minute walk to Prospect Park, minutes from great walking "
              "streets on Vanderbilt and Washington. 7 minutes to B, Q train; 9 minutes to 2, 3 train; "
              "13 minutes to all trains at Atlantic Barclays. I’m looking for someone quiet, clean, "
              "and respectful! If interested please tell me a little about yourself! Please no “is "
              "this still available inquiries.” I will take it down once someone has taken it.",
    ),
    _cl(  # cRqHLJgf7Jvszsqp56LVeD (live)
        why="Thanksgiving-week 1BR $1,500, a 4th-floor walk-up: short stay",
        title="Thanksgiving week sublet - November 22-30",
        price=1500,
        bedrooms=1,
        category="sublets",
        attrs={"laundry": ["5", "no laundry on site"], "parking": ["7", "no parking"]},
        body="Light-flooded one bedroom apartment available for sublet Thanksgiving week (November "
              "22-30). This is a 4th floor walkup in a small modern building with friendly neighbors. "
              "The apartment is well-furnished and user-friendly and has a small balcony. Priority "
              "will be given to a sub-letter who is mature and conscientious.",
    ),
    _cl(  # 9nQE9ASJvGuiQdEZ4F3PED (live)
        why="Williamsburg 1BR $1,500 Oct 15 - Nov 1 'for a few weeks': short stay",
        title="OCT 15 - NOV 1: Furnished Williamsburg 1BR – W/D, Dishwasher",
        price=1500,
        category="sublets",
        attrs={"laundry": ["1", "w/d in unit"], "parking": ["7", "no parking"]},
        body="Subletting my fully furnished one-bedroom apartment in Williamsburg while I travel for "
              "a few weeks, from Thursday, Oct 15, to Sunday, November 1 ($1,500). All utilities "
              "included, plus in-unit washer/dryer and dishwasher. The apartment has a comfortable "
              "living area and a dedicated desk setup for working from home. – 5-minute walk to Marcy "
              "Ave J/Z train – 10-minute walk to Bedford Ave L train – 3 blocks to the Williamsburg "
              "Bridge (pedestrian and bike access) Located on the 4th floor of a walkup; good natural "
              "light and no upstairs neighbors. Couples OK. No pets or children. Happy to share a "
              "video tour. Please include a brief intro about yourself in your first message.",
    ),
    _cl(  # dj4JU2FVswazdLocyjPNnF (live)
        why="Crown Heights studio $1,500 for 10/27-11/13: short stay",
        title="Studio Apartment Sublet (10/27-11/13)",
        price=1500,
        category="sublets",
        attrs={"laundry": ["2", "laundry in bldg"], "parking": ["5", "street parking"]},
        body="Dates: 10/27-11-13 **Ideally you stay the full duration but I'm willing to negotiate** "
              "Subletting my spacious studio located in Crown Heights off of the Nostrand (3), "
              "President (2)(5), and Franklin Ave (2)(3)(4)(5). Separate living area, ample closet "
              "space, laundry in basement, and rooftop access. Old school charming building close to "
              "everything: bars, restaurants, yoga studios, good groceries, and amazing culture. $1500 "
              "for the duration, which includes utilities. Refundable deposit of $1000, will be "
              "returned if apartment is in tidy condition with no damages.",
    ),
    _cl(  # ax74PZRKEZMMdPNYVsBNdB (cached first 300 chars; post removed)
        why="A lister warning about a copycat of their own ad",
        title="PLEASE BE ADVICE OF SCAM WHICH IS USING MY AD",
        neighborhood="Brooklyn",
        price=899,
        body="PLEASE BE ADVICE OF A SCAMMER WHO IS USING MY AD AND ADVERTISING IT FOR JUST $650! IT "
              "IS A SCAM! HE WILL BE ASKING YOU FOR YOUR PHONE NUMBER AN WILL NEVER SHOW YOU THE ROOM "
              "SINCE IT'S MY ROOM. ANYTHING ADVERTISED BELOW MY PRICE WHICH IS $1260 (FOR MY AD) IS A "
              "SCAM! BE AWARE",
    ),
    _cl(  # evmMsKWeHLrXb69ws3aQ1D (live)
        why="East Village 1BR by the night, 'no fee Zelle/Venmo': a caution, not proof",
        title="$199 / 1br - 450ft2 - Very Spacious EntireApt East Village 1 flight-up",
        price=199,
        bedrooms=1,
        category="sublets",
        attrs={"rent_period": ["1", "daily"], "laundry": ["5", "no laundry on site"], "parking": ["5", "street parking"]},
        body="Hello! I am renting out my East Village 1-bedroom, the entire apartment. 15 nights is "
              "next available opening starting in December. Next available opening: ****Friday, "
              "December 18th, 2026*** to checkout on Saturday January, 2nd, 2027.  (15 nights) 4-night "
              "minimum stay, and discount for weekly, and bigger discount for monthly. See my website "
              "calendar for availability: [link] Feel free to message me if you have any questions. "
              "[link] (bookmark my link!) Rates subject to change but generally: (rate 1) 4 nights to "
              "6nts: $229/nt (rate 2) $209/nt (rate 3) $179/nt (rate 4) $169/nt (rate 5) $159/nt (rate "
              "6) $139/nt Fees: +$25/nt for 3rd guest adult / child These fees also drop with rates "
              "(for longer stays) 3% credit card transaction fee, no fee Zelle/Venmo About the "
              "apartment: Located in the heart of the East Village, between 3rd Ave and Ave C, between "
              "14th and 1st streets. Exact address provided upon booking. Quiet, well-cared for "
              "1-bedroom, 1 bath, full kitchen with breakfast nook, backyard, queen bed, two fold out "
              "futons. High speed Wifi internet and two smart TVs. Only 1 flight up! All uti",
    ),
    _cl(  # h8c2j9FcxdmzVYXFhBj4bG (cached first 300 chars; post removed)
        why="Greenpoint room $1,800 '30 minutes to Union Square', G train: routed to Manhattan, not "
             "lying",
        title="Greenpoint room",
        neighborhood="Greenpoint",
        price=1800,
        body="Finished  room, 20 minutes  to midtown, 30 minutes to. Union Square .  Share kitchen.  "
              "Two Bathrooms. One block to G train at Greenpoint subway station. Many shops : Bars, "
              "restaurants , Coffee shops, Laundromat, Clothing shop, food markets, banks etc. one "
              "block to park / wa",
    ),
    _cl(  # a8qYTnhXgzXWje4B5UNhXA (cached first 300 chars; post removed)
        why="Crown Heights room $1,300, 2 & 5 trains on the corner",
        title="Crown Heights Sublet",
        neighborhood="Crown Heights",
        price=1300,
        body="Crown Heights Sublet: 10/10 - 12/10 1 Bedroom in 3 Bed 1 Bath 10 minute walk from "
              "Prospect Park 🌿 Easy access to trains! 2 & 5 trains right on the corner, rest of number "
              "trains 2 blocks away. Straight shot to Manhattan and 2 stops away from major connecting "
              "trains to the re",
    ),
    _cl(  # 5UNRLpfmzCQhDRr8HNQ6d4 (live)
        why="Clinton Hill room $1,300 'close to both Fort Greene park and Prospect park'",
        title="Lovely room for rent in my 2 BR available November 4 (3-6 month stay)",
        price=1300,
        bedrooms=1,
        category="rooms",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["5", "no laundry on site"], "parking": ["5", "street parking"]},
        body="Hi, I am a friendly, clean, and easy going male artist with an available spare bedroom "
              "for rent beginning November 6, 2026. This is for one private bedroom in my 2 bedroom "
              "apartment on the 3rd floor of a three story prewar walk up in Clinton Hill, Brooklyn. I "
              "am the leaseholder and the only other person living here. The room is available for 3 "
              "months minimum, and up to 6 months. The room for rent is lovely and quiet, as it does "
              "not face the street. It is very clean and furnished with a full sized bed, an armoire "
              "with plenty of hanging and shelf space, a coat rack, and a table. The room dimensions "
              "are about 10 x12 feet (120 sq ft) with two large windows and nice light coming in all "
              "day. The shared space is a fully functioning/equipped eat-in kitchen, and bathroom "
              "(shower and full bathtub). This is perfect for someone who wants to explore the "
              "neighborhood and get a feel for living in Clinton Hill/Bed-Stuy, and a great spot for "
              "someone who is traveling or between apartments. The building is one block away from the "
              "G train and about 15 minutes to the C train. There are plenty of bus line",
    ),
    _cl(  # spqtwTQRBwaEp7ibDmgqB3 (live)
        why="Greenpoint room $1,350 near the G, laundromats nearby",
        title="Cozy Greenpoint Bedroom Available Nov 1",
        price=1350,
        category="rooms",
        attrs={"laundry": ["5", "no laundry on site"], "parking": ["5", "street parking"]},
        body="We are two roommates living in Greenpoint looking for a third roommate (we are looking "
              "for just one roommate) to move in Nov for 2-3 months to start. We will be only looking "
              "for a woman in her early 30's with a full time job that DOES NOT work from home. Our "
              "apartment is 3 bedrooms. The apartment is on the 3rd floor and has a nice sized kitchen "
              "and dining room. There is one bathroom that is shared. We live half a block away from "
              "the Greenpoint Ave G train. There are many laundromats within a few blocks of the "
              "building. Our shared space is often clean with little to no dishes in the sink and "
              "tidy. We are a quiet bunch at home and will be looking for someone who shares our "
              "vision for a quiet space. There's no smoking in the apartment and we would prefer a "
              "roommate that doesn't bring the party home. We like to surf, travel, design and make "
              "food in our free time. Although we love pets, the building does not allow them, so NO "
              "PETS. Rent is 1,350 without utilities. Deposit is 1,350. Usually around $50/month The "
              "room is cozy and comfortable with one window. It will be non furnished. The liv",
    ),
    _cl(  # vimaDPFRm1DRPnrNU2Bxrc (live)
        why="Prospect Lefferts Gardens room $1,500 in a 3BR",
        title="Bedroom available in 1200 ft.² three bedroom apartment",
        price=1500,
        bedrooms=1,
        category="rooms",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["1", "w/d in unit"], "parking": ["5", "street parking"]},
        body="There is one room available in our 1200 sq ft three-bedroom apartment in Prospect "
              "Lefferts Gardens. The apartment is in a three-story, classic Brooklyn limestone "
              "building. You'd be sharing one of the floors with two roommates on the 2nd floor. While "
              "in an active neighborhood, it's situated near the back of a dead-end street, allowing "
              "for quiet time at home while still having everything within walking distance of your "
              "door. The room measures 144 sq. ft., is situated at the back of the apartment, facing a "
              "quiet, shady courtyard with a view of a nearby bamboo garden. There is a 180 sq. ft. "
              "deck, which is shared between the room and mine. The bedroom features exposed brick and "
              "a large sliding-door closet, offering ample storage space. The apartment had a major "
              "kitchen and living room renovation last Fall. The kitchen features a Miele washer and "
              "dryer, a Bosch dishwasher, and a quartz countertop. There are hardwood floors "
              "throughout and extra storage in the basement if needed. The monthly rent is $1,500 with "
              "a move-in date of Nov. 1st. We would prefer a long-term roommate. The neighborhoo",
    ),
    _cl(  # x1BiQtnSHGPih1q6oRV2KJ (live)
        why="Crown Heights room $1,300 in a 5BR",
        title="Subletting spacious, unfurnished room in Crown Heights - $1,300/month",
        price=1300,
        bedrooms=5,
        category="sublets",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["1", "w/d in unit"], "parking": ["7", "no parking"]},
        body="Hi! I’m subletting a spacious, unfurnished room in a 5bed/3bath apartment in Crown "
              "Heights — available immediately. Rent will be $1,300/month (prorated for October, of "
              "course). The apartment is a second-floor walk-up in a pre-war building currently "
              "occupied by four young professionals (3M/1F) -- we just started our lease and are "
              "looking for someone to hold a room before the final roommate moves in. The room is "
              "~9x11 feet. It comfortably fits a full bed and has a massive closet. There are two "
              "large windows, so you would get lots of light. You would share a bathroom with one "
              "other person. The kitchen is well-equipped, and the common space is quickly coming "
              "together. Transit: - 5min from Kingston Ave C stop - 10min from Utica Ave and Nostrand "
              "A stops - 15min from Kingston Ave 3/4 stop - Within blocks of several bus lines (B43, "
              "B44, B65) Appliances are all new and high-quality: - Dishwasher - In-unit washer and "
              "dryer - Split A/C and heating Right near Brower Park and St. John’s Park, and lots of "
              "activity in the area (small businesses, delis, and grocery store!). One of the "
              "roommates has ",
    ),
    _cl(  # 8jJKj1kMwREvnsQeRhZ5bv (live)
        why="LES studio $1,000 for one week over NYE: short stay",
        title="1 week sublet offered, NYE holidays",
        price=1000,
        bedrooms=1,
        category="sublets",
        attrs={"laundry": ["5", "no laundry on site"], "parking": ["5", "street parking"]},
        body="Hi! I’m looking to find a kind, trustworthy and reliable subletter to rent out my cozy, "
              "fully furnished studio in prime lower east side, Manhattan. I love this space and hope "
              "to fill it for 5 nights while I’m out of town! December 28-January 2. Amazing night "
              "life and restaurants all within walking distance. $1000 for 5 nights.",
    ),
]

# Not judged themselves: siblings the template check needs in the same batch
BATCH = [
    _cl(  # bnynxskKzHD1beUjPT1Fen (live)
        why="Tribeca copy of the $1,700 template (live)",
        title="1-bed 1-bath sublet mid to end Sept until.2027 sublet in Tribeca",
        price=1700,
        bedrooms=1,
        category="sublets",
        attrs={"rent_period": ["3", "monthly"], "laundry": ["1", "w/d in unit"], "parking": ["1", "carport"], "wheelchaccess": ["1", "wheelchair accessible"]},
        body="Private apartment available anytime between mid to end September - 2027 $1700 per "
              "month, which covers rent, utilities, and 1Gb internet (price negotiable for longer "
              "periods) Apartment is furnished, but includes a full kitchen with standard appliances. "
              "Great location with public transit options. (Located near all major transportation "
              "including the 1, 6, N, Q, J, Z trains.) Note: A/C is included.",
    ),
    _cl(  # vCtrZzJPJ15GPKLUWS8MoB (cached first 300 chars; post removed)
        why="Staten Island copy of the $1,700 template",
        title="1-bed 1-bath sublet mid to end Sept until.2027 sublet in Staten",
        neighborhood="Staten Island",
        price=1700,
        body="Private apartment available anytime between mid to end September - 2027 $1700 per "
              "month, which covers rent, utilities, and 1Gb internet (price negotiable for longer "
              "periods) Apartment is furnished, but includes a full kitchen with standard appliances. "
              "Great location with pu",
    ),
]


def _listing(title: str, body: str = "", **fields) -> Listing:
    return Listing(id=title, source="craigslist_nyc", url="", title=title, body=body,
                   body_snippet=body[:300], **fields)


def _score(l: Listing, families=None) -> tuple[int, list[str]]:
    _, hood = _assign_region(" ".join(filter(None, [l.title, l.neighborhood, l.body])))
    reasons = scam.assess(l, hood, families)
    return sum(p for p, _ in reasons), [r for _, r in reasons]


# (check, expected, why) — one rule or guard at a time
GUARDS = [
    # What is being rented
    (lambda: scam.unit_kind(_listing("Sunny Bedroom in Luxury South Slope High Rise Apt", bedrooms=1)),
     "room", "room wording in the title beats CL's 1BR housing line"),
    (lambda: scam.unit_kind(_listing("Gorgeous 1 bedroom apartment", "Windows in every room.")),
     "1br", "'every room' is not a room for rent"),
    (lambda: scam.unit_kind(_listing("Quiet place near the park", category="rooms", bedrooms=0)),
     "room", "rooms & shares: the 0BR housing line means nothing"),
    (lambda: scam.unit_kind(_listing("2BR SHARE")), "room", "a share is a room"),
    (lambda: scam.unit_kind(_listing("A nice furnished living room available", "1 bedroom plus office")),
     "room", "renting out a living room"),
    # Short stays are priced per stay
    (lambda: scam.is_short_stay(_listing("1BR, Nov 20-29")), True, "month-name range"),
    (lambda: scam.is_short_stay(_listing("Studio Apartment Sublet (10/27-11/13)")), True, "numeric range"),
    (lambda: scam.is_short_stay(_listing("Studio, Jan 19 through May 18")), False, "four months is not short"),
    (lambda: scam.is_short_stay(_listing("1BR", "while I travel for a few weeks")), True, "'a few weeks'"),
    (lambda: scam.is_short_stay(_listing("1BR", attrs={"rent_period": ["1", "daily"]})), True,
     "CL rent period: daily"),
    # Subway lines
    (lambda: scam.lines_named("next to 1,2,3 trains"), {"1", "2", "3"}, "comma list"),
    (lambda: scam.lines_named("72nd Street (1/2/3 and B/C trains)"), {"1", "2", "3", "B", "C"}, "slash groups"),
    (lambda: scam.lines_named("A/C, W/D, dishwasher"), set(), "air conditioning and washer/dryer"),
    (lambda: scam.lines_named("2 stops from Union Square"), set(), "a count, not the 2 train"),
    (lambda: scam.lines_named("2 short blocks from the 7"), set(), "cut off: it was '7th Avenue'"),
    (lambda: _score(_listing("Finished room, 30 minutes to Union Square",
                             "One block to G train at Greenpoint subway station."))[0], 0,
     "routed to Union Square, but names both sides of the river: stands down"),
    # Where the place is
    (lambda: scam.located_area(_listing("Secret Garden Room", "3 blocks from Prospect Park. It takes "
                                        "approximately 25 minutes to reach the LES.")), None,
     "a commute is not the location"),
    # Landmarks
    (lambda: _score(_listing("Studio in East Village", "Quiet apartment close to Central Park."))[1],
     ["describes Central Park — not near East Village"], "proximity wording, wrong part of town"),
    (lambda: _score(_listing("Studio in East Village", "20 minutes by train to Central Park."))[0], 0,
     "a commute to a landmark is fine"),
    # Tags
    (lambda: _score(_listing("Room in Crown Heights", attrs={"parking": ["2", "attached garage"],
                                                              "ev_charging": ["1", "ev charging"]}))[0],
     0, "South Brooklyn is exempt from the garage/EV signal"),
    (lambda: _score(_listing("Room in Fort Greene", attrs={"parking": ["2", "attached garage"],
                                                            "ev_charging": ["1", "ev charging"]}))[0],
     2, "garage + EV elsewhere, capped at 2"),
    # Craigslist only
    (lambda: filter_listings([Listing(id="sr", source="spareroom", url="", price=900,
                                      title="Studio in East Village, Zelle only",
                                      body_snippet="Keys will be mailed to you. Studio in East Village.")])[0].scam_score,
     0, "non-Craigslist sources are never scored"),
    # Flagged posts are not emailed
    (lambda: filter_listings([_listing("Furnished room in Fort Greene", "Sunny furnished room in a quiet "
                                       "apartment. I travel for work, so the keys will be mailed to you.",
                                       price=1200)]),
     [], "a flagged Craigslist post (score 3) is dropped, not emailed (SCAM_DROP_SCORE)"),
    (lambda: len(filter_listings([_listing("Furnished room in Fort Greene", "Sunny furnished room in a "
                                           "quiet apartment. Happy to show it any evening this week.",
                                           price=1200)])),
     1, "the same post without the keys line is still emailed"),
]


def _template_guard() -> bool:
    """Border lister reposting one room as Bushwick and as Bed-Stuy: not a swap."""
    text = ("Quiet room located in a peaceful, sunny townhouse in Ocean Hill, nestled between BedStuy, "
            "Bushwick, and Crown Heights. This listing is for an unfurnished room in a walkthrough "
            "apartment with three roommates in total. The room is the middle room in the apartment "
            "and does not have a window, see pictures. Newly painted, ceiling fan, kitchen with "
            "garden view and morning sunlight, very nice roommates, high-speed internet.")
    a = _listing("Room in quiet Townhouse, BUSHWICK", text)
    b = _listing("Room in quiet townhouse, Bed-Stuy", text)
    return not scam.template_families([a, b])


def main() -> int:
    batch = [l for l, _ in CONFIRMED + JUDGED + LEGIT + BATCH]
    families = scam.template_families(batch)
    failures = 0
    totals = {}
    for name, cases, want_flag in (("CONFIRMED", CONFIRMED, True), ("JUDGED", JUDGED, True),
                                   ("LEGIT", LEGIT, False)):
        print(f"\n── {name} ──")
        ok_count = 0
        for l, why in cases:
            score, reasons = _score(l, families)
            flagged = score >= config.SCAM_FLAG_SCORE
            ok = flagged == want_flag
            ok_count += ok
            failures += not ok
            print(f"{'ok  ' if ok else 'FAIL'}  {score:>2}  {why[:72]}")
            if not ok or (flagged and name != "LEGIT" and "-v" in __import__("sys").argv):
                for r in reasons:
                    print(f"            · {r}")
        totals[name] = (ok_count, len(cases))

    print("\n── GUARDS ──")
    for check, expected, why in GUARDS:
        got = check()
        ok = got == expected
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'}  {why}" + ("" if ok else f"  → got {got!r}, expected {expected!r}"))
    ok = _template_guard()
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'}  areas named together in one post are one place (template check)")

    c, j, g = totals["CONFIRMED"], totals["JUDGED"], totals["LEGIT"]
    summary = (f"{c[0]}/{c[1]} confirmed and {j[0]}/{j[1]} judged scams flagged, "
               f"{g[0]}/{g[1]} legit posts clean, {len(GUARDS) + 1} guards")
    print(f"\n{'✅' if not failures else '❌'} {summary}" + (f" — {failures} failure(s)" if failures else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
