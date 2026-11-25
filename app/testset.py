"""The test set: sentences recorded by real speakers (labelled by speaker and style) to measure
how well each accent feature is detected. Focused on Indian English first.

Each item lists the features it targets (see eval/features in scripts/eval.py):
  aspiration  P, T, K with a puff of air (pin, ten, cat)
  th          TH / DH as hiss or buzz, not a stop (think, this)
  vw          V with friction vs W as a lip glide (very, west)
  dark_l      L after a vowel (feel, milk, all)
  r           American R and "er"
  ey_ow       the glides in "day" and "go"
  ae          the A in "cat"
  aa          the O in "hot"
  ah          the U in "cup"
  ih_iy       sit / seat
  uh_uw       full / fool
  z           final Z (dogs, is)
  flap        the soft T in "water"
  stress      word stress and weak forms
"""

TESTSET: list[dict] = [
    # Aspiration: P, T, K at the start of a word or a stressed syllable
    {"id": "asp-01", "text": "Peter put the paper in his pocket.", "features": ["aspiration"]},
    {"id": "asp-02", "text": "Kate keeps the keys in the kitchen.", "features": ["aspiration"]},
    {"id": "asp-03", "text": "Take two tickets to Texas.", "features": ["aspiration"]},
    {"id": "asp-04", "text": "Paul parked by the park in the pouring rain.", "features": ["aspiration", "dark_l", "r"]},
    {"id": "asp-05", "text": "Carl called the company to complain.", "features": ["aspiration", "dark_l"]},
    {"id": "asp-06", "text": "Tom told Tina a terrible tale.", "features": ["aspiration", "dark_l"]},
    {"id": "asp-07", "text": "The cat caught a cold in the cave.", "features": ["aspiration", "ae"]},
    {"id": "asp-08", "text": "Please pass the pepper and the potatoes.", "features": ["aspiration", "z"]},
    {"id": "asp-09", "text": "Kevin counted the coins carefully.", "features": ["aspiration"]},
    {"id": "asp-10", "text": "Turn on the TV at ten.", "features": ["aspiration"]},
    # TH and DH
    {"id": "th-01", "text": "I think these three things are worth thinking about.", "features": ["th"]},
    {"id": "th-02", "text": "They thought the theater was through the other path.", "features": ["th"]},
    {"id": "th-03", "text": "This is the thirteenth Thursday of the month.", "features": ["th"]},
    {"id": "th-04", "text": "Both brothers breathe through their mouths.", "features": ["th"]},
    {"id": "th-05", "text": "Thank them for the thoughtful gift.", "features": ["th"]},
    {"id": "th-06", "text": "The weather was rather smooth this month.", "features": ["th"]},
    {"id": "th-07", "text": "Is that the method they used?", "features": ["th"]},
    {"id": "th-08", "text": "Nothing else matters to them.", "features": ["th"]},
    # V and W
    {"id": "vw-01", "text": "Victor visited a village in the valley.", "features": ["vw"]},
    {"id": "vw-02", "text": "We were wondering where the waiter went.", "features": ["vw"]},
    {"id": "vw-03", "text": "Very few voters were aware of the vote.", "features": ["vw", "r"]},
    {"id": "vw-04", "text": "Will was waiting with a warm vest.", "features": ["vw"]},
    {"id": "vw-05", "text": "Wednesday was a very wet and windy day.", "features": ["vw"]},
    {"id": "vw-06", "text": "Vivian wore a violet velvet veil.", "features": ["vw", "dark_l"]},
    {"id": "vw-07", "text": "The van went west on the wide avenue.", "features": ["vw"]},
    {"id": "vw-08", "text": "I would value a quiet evening with wine.", "features": ["vw"]},
    # Dark L
    {"id": "l-01", "text": "I feel cold, so I'll call you later.", "features": ["dark_l"]},
    {"id": "l-02", "text": "Bill spilled the milk on the table.", "features": ["dark_l"]},
    {"id": "l-03", "text": "The whole school will help the people.", "features": ["dark_l"]},
    {"id": "l-04", "text": "Fill the bottle with cool water.", "features": ["dark_l", "flap"]},
    {"id": "l-05", "text": "Al sold all the old bicycles.", "features": ["dark_l"]},
    {"id": "l-06", "text": "The little girl smiled at the doll.", "features": ["dark_l"]},
    {"id": "l-07", "text": "It was a long, full, beautiful hill.", "features": ["dark_l"]},
    {"id": "l-08", "text": "Please tell Paul to feel well.", "features": ["dark_l", "aspiration"]},
    # R (regression checks for the existing R measurement)
    {"id": "r-01", "text": "Robert drove his red truck across the river.", "features": ["r"]},
    {"id": "r-02", "text": "Her brother works hard in the early morning.", "features": ["r"]},
    {"id": "r-03", "text": "The farmer parked his car near the barn.", "features": ["r"]},
    {"id": "r-04", "text": "Are you sure you're ready for the storm?", "features": ["r"]},
    # Vowels
    {"id": "v-01", "text": "The rain in May made the day gray.", "features": ["ey_ow"]},
    {"id": "v-02", "text": "Go home and close the window slowly.", "features": ["ey_ow"]},
    {"id": "v-03", "text": "They stayed late to paint the gate.", "features": ["ey_ow"]},
    {"id": "v-04", "text": "Joe told me he's going to Rome.", "features": ["ey_ow"]},
    {"id": "v-05", "text": "The black cat sat on the mat.", "features": ["ae"]},
    {"id": "v-06", "text": "Dan has a bad habit of laughing at ads.", "features": ["ae"]},
    {"id": "v-07", "text": "Tom got a hot cup of coffee.", "features": ["aa", "ah"]},
    {"id": "v-08", "text": "Stop the clock on the top shelf.", "features": ["aa"]},
    {"id": "v-09", "text": "Some young customers come on Sunday.", "features": ["ah"]},
    {"id": "v-10", "text": "Please sit in the seat and eat a bit.", "features": ["ih_iy"]},
    {"id": "v-11", "text": "Will you fill it or feel it?", "features": ["ih_iy", "dark_l"]},
    {"id": "v-12", "text": "The cook put the food in the pool.", "features": ["uh_uw"]},
    # Final Z, the soft T
    {"id": "z-01", "text": "His dogs and cats always play in the yards.", "features": ["z"]},
    {"id": "z-02", "text": "She buys roses for her friends.", "features": ["z"]},
    {"id": "f-01", "text": "I bought a bottle of water and a little butter.", "features": ["flap"]},
    {"id": "f-02", "text": "Get it out of the city.", "features": ["flap"]},
    # Stress and weak forms
    {"id": "s-01", "text": "I want to go to the store and get some bread.", "features": ["stress"]},
    {"id": "s-02", "text": "The photographer took a photograph of the class.", "features": ["stress"]},
    {"id": "s-03", "text": "We need to develop a better economy.", "features": ["stress"]},
    {"id": "s-04", "text": "Can you tell me what time it is?", "features": ["stress", "aspiration"]},
    {"id": "s-05", "text": "I'd like a cup of tea and a piece of cake.", "features": ["stress", "aspiration"]},
    {"id": "s-06", "text": "He was asked to come to the meeting at four.", "features": ["stress"]},
]

SPEAKERS = ["me", "friend", "other"]
STYLES = {
    "natural": "My normal way",
    "american": "My best American",
}
