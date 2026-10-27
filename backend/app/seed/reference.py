"""Static reference data for the synthetic demo generator.

City centroids are approximate public geographic coordinates (city level only) used to give synthetic donors an
area-level location for distance ranking. Localities are generic area names used for display only.
Organisation names are invented from neutral word pools and always carry a "(Demo)" suffix; they are not real
facilities. Personal names are random combinations of common given names and family names and do not refer to
real people.
"""

# name, latitude, longitude, relative weight (roughly proportional to urban population), localities
CITIES: list[tuple[str, float, float, int, list[str]]] = [
    (
        "Karachi",
        24.86,
        67.01,
        160,
        ["Clifton", "Gulshan-e-Iqbal", "North Nazimabad", "Korangi", "Malir", "Saddar", "PECHS", "Gulistan-e-Johar"],
    ),
    ("Lahore", 31.55, 74.34, 110, ["Gulberg", "Model Town", "Johar Town", "DHA", "Iqbal Town", "Shadman", "Township", "Samanabad"]),
    ("Faisalabad", 31.42, 73.08, 32, ["Peoples Colony", "Madina Town", "Ghulam Muhammad Abad", "Satiana Road", "D Ground"]),
    ("Rawalpindi", 33.60, 73.04, 22, ["Satellite Town", "Saddar", "Bahria Town", "Chaklala", "Westridge", "Committee Chowk"]),
    ("Islamabad", 33.69, 73.05, 20, ["F-7", "G-9", "I-8", "G-11", "F-10", "E-11", "Bahria Enclave", "PWD"]),
    ("Gujranwala", 32.16, 74.19, 20, ["Satellite Town", "Model Town", "Peoples Colony", "Civil Lines"]),
    ("Multan", 30.20, 71.47, 19, ["Cantt", "Gulgasht", "Bosan Road", "Shah Rukn-e-Alam", "New Multan"]),
    ("Hyderabad", 25.40, 68.37, 18, ["Latifabad", "Qasimabad", "Saddar", "Hirabad"]),
    ("Peshawar", 34.01, 71.58, 19, ["Hayatabad", "University Town", "Saddar", "Gulbahar", "Warsak Road"]),
    ("Quetta", 30.18, 66.98, 10, ["Jinnah Town", "Satellite Town", "Samungli Road", "Brewery Road"]),
    ("Sialkot", 32.49, 74.53, 7, ["Cantt", "Model Town", "Paris Road"]),
    ("Bahawalpur", 29.40, 71.68, 7, ["Model Town", "Satellite Town", "Cantt"]),
    ("Sargodha", 32.08, 72.67, 7, ["Satellite Town", "Block 7", "University Road"]),
    ("Abbottabad", 34.15, 73.22, 4, ["Jinnahabad", "Cantt", "Mandian"]),
    ("Sukkur", 27.71, 68.85, 5, ["Military Road", "Old Sukkur", "Barrage Colony"]),
]

# Approximate Pakistani blood-group distribution, used as sampling weights (sums to 1000).
BLOOD_GROUP_WEIGHTS: dict[str, int] = {"B+": 300, "O+": 285, "A+": 215, "AB+": 80, "O-": 40, "B-": 35, "A-": 30, "AB-": 15}

GIVEN_NAMES_F = [
    "Ayesha",
    "Fatima",
    "Zainab",
    "Maryam",
    "Hira",
    "Sana",
    "Amna",
    "Iqra",
    "Mahnoor",
    "Sadia",
    "Rabia",
    "Nida",
    "Khadija",
    "Saba",
    "Sidra",
    "Areeba",
    "Fiza",
    "Kiran",
    "Laiba",
    "Mehwish",
    "Noor",
    "Rida",
    "Sobia",
    "Uzma",
]
GIVEN_NAMES_M = [
    "Muhammad",
    "Ahmed",
    "Ali",
    "Hassan",
    "Usman",
    "Bilal",
    "Hamza",
    "Umar",
    "Zain",
    "Saad",
    "Faisal",
    "Imran",
    "Kashif",
    "Asad",
    "Junaid",
    "Waqas",
    "Adeel",
    "Danish",
    "Farhan",
    "Haris",
    "Kamran",
    "Nadeem",
    "Rizwan",
    "Tariq",
    "Shahid",
    "Yasir",
    "Zubair",
    "Arslan",
    "Babar",
    "Fahad",
]
FAMILY_NAMES = [
    "Khan",
    "Ahmed",
    "Hussain",
    "Malik",
    "Qureshi",
    "Siddiqui",
    "Sheikh",
    "Chaudhry",
    "Butt",
    "Raza",
    "Abbasi",
    "Awan",
    "Baig",
    "Mirza",
    "Rana",
    "Javed",
    "Iqbal",
    "Aslam",
    "Akhtar",
    "Shah",
    "Bukhari",
    "Gillani",
    "Hashmi",
    "Kazmi",
    "Memon",
    "Baloch",
    "Yousafzai",
    "Afridi",
    "Durrani",
    "Niazi",
    "Bhatti",
    "Cheema",
    "Warraich",
    "Lodhi",
    "Soomro",
]

ORG_WORDS = [
    "Crescent",
    "Lifeline",
    "Harmony",
    "Evergreen",
    "Silverline",
    "Northstar",
    "Riverside",
    "Cedar",
    "Summit",
    "Beacon",
    "Meridian",
    "Compass",
    "Horizon",
    "Keystone",
    "Lantern",
    "Oasis",
]
ORG_FORMS = [
    ("blood_bank", "Blood Centre"),
    ("blood_bank", "Regional Blood Bank"),
    ("hospital_blood_bank", "Teaching Hospital Blood Bank"),
    ("hospital_blood_bank", "General Hospital Transfusion Unit"),
    ("hospital", "Medical Complex"),
]

HOSPITAL_SUFFIXES = ["General Hospital", "Medical Centre", "Teaching Hospital", "Children's Hospital", "Women's Hospital"]

RELATIONSHIPS = ["Parent", "Sibling", "Spouse", "Child", "Relative", "Friend", "Hospital staff"]

# Typical shelf life in days by component (operational defaults; actual limits depend on processing and storage).
SHELF_LIFE_DAYS: dict[str, int] = {
    "whole_blood": 35,
    "red_cells": 42,
    "plasma": 365,
    "platelets": 5,
    "cryoprecipitate": 365,
}

# Relative share of inventory batches by component.
COMPONENT_WEIGHTS: dict[str, int] = {"red_cells": 40, "whole_blood": 22, "plasma": 22, "platelets": 10, "cryoprecipitate": 6}
