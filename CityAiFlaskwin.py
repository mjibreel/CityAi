import pyttsx3
from gtts import gTTS
import os
import pygame
import speech_recognition as sr
import webbrowser
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_bootstrap import Bootstrap
# from google.cloud import texttospeech
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError

# Initialize recognizer and TTS engine
recognizer = sr.Recognizer()
microphone = sr.Microphone()

def initialize_voice_engine():
    """Initialize the TTS engine with desired settings."""
    engine = pyttsx3.init('sapi5')
    voices = engine.getProperty('voices')
    
    # Set to female voice if available
    female_voice = next((voice for voice in voices if 'female' in voice.name.lower()), None)
    engine.setProperty('voice', female_voice.id if female_voice else voices[1].id)  # Default to the second voice (adjust as needed)
    
    # Adjust volume and speed
    engine.setProperty('volume', 1.0)
    engine.setProperty('rate', 150)
    return engine

engine = initialize_voice_engine()  # Initialize global TTS engine

# Dictionary to store language-specific voices
language_voices = {
    'en': None,  # English voice
    'ar': None,  # Arabic voice
    'ms': None   # Malay voice
}

def initialize_multilingual_engine():
    voices = engine.getProperty('voices')
    for voice in voices:
        if 'english' in voice.name.lower():
            language_voices['en'] = voice.id
        elif 'arabic' in voice.name.lower():
            language_voices['ar'] = voice.id
        elif 'malay' in voice.name.lower() or 'indonesian' in voice.name.lower():
            language_voices['ms'] = voice.id

def speak(text, language='en'):
    try:
        # Generate speech using gTTS
        tts = gTTS(text=text, lang=language, slow=False)
        
        # Save the generated speech as an MP3 file
        temp_file = "temp.mp3"
        tts.save(temp_file)
        
     # Initialize pygame mixer and play the audio
        pygame.mixer.init()
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()

        # Wait for the audio to finish
        while pygame.mixer.music.get_busy():
            pass

        # Clean up
        pygame.mixer.quit()
        os.remove(temp_file)

        # Play the audio file
        # os.system(f"start {temp_file}")  # 'start' for Windows, 'afplay' for macOS, or 'mpg123' for Linux
    except Exception as e:
        print(f"Error in generating speech: {e}")
    if language in language_voices and language_voices[language]:
        # engine.setProperty('voice', language_voices[language])
        pyttsx3_speak(text)



def pyttsx3_speak(text):
    """
    Speak function for pyttsx3 (used as fallback or for specific languages).
    """
    try:
        engine.say(text)
        engine.runAndWait()
    except RuntimeError:
        print("Pyttsx3 engine already running; restarting.")
        engine.stop()
        engine.say(text)
        engine.runAndWait()




def listen_for_keyword(keyword="city"):
    """
    Listen for a specific keyword and respond when detected.
    Keeps listening until the keyword is recognized.
    """
    while True:
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            print("Listening for the keyword...")
            try:
                audio = recognizer.listen(source)
                query = recognizer.recognize_google(audio, language='en-US').lower()
                print(f"User said: {query}")
                if keyword in query:
                    speak("Yes, how can I assist you?")
                    return query
            except sr.UnknownValueError:
                print("Could not understand audio. Waiting for the keyword...")
            except sr.RequestError as e:
                print(f"Error with speech recognition service: {e}")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

def recognize_speech():
    """
    Capture and recognize user speech for a query.
    Returns the recognized text or "None" on failure.
    """
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening for query...")
        try:
            audio = recognizer.listen(source)
            query = recognizer.recognize_google(audio, language='en-US').lower()
            print(f"User said: {query}")
            return query
        except sr.UnknownValueError:
            print("Sorry, I did not understand that.")
            return "None"
        except sr.RequestError as e:
            print(f"Could not request results; {e}")
            return "None"
        except Exception as e:
            print(f"An error occurred: {e}")
            return "None"

def recognize_speech_from_mic():
    """Transcribes speech from the microphone."""
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening...")
        audio = recognizer.listen(source)
    
    try:
        transcription = recognizer.recognize_google(audio)
        print(f"You said: {transcription}")
        return transcription.lower()
    except sr.UnknownValueError:
        print("Sorry, I didn't catch that.")
        return None
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return None



# # Global dictionary to store last interaction times
user_interactions = {}
# cityAi = Flask(__name__, template_folder='/Users/jibre/OneDrive/Desktop/NewCityAi/venv/templates', static_folder='/Users/jibre/OneDrive/Desktop/NewCityAi/static')
cityAi = Flask(
    __name__,
    template_folder=r'C:\Users\jibre\OneDrive\Desktop\cityAi\templates',
    static_folder=r'C:\Users\jibre\OneDrive\Desktop\cityAi\static')

bootstrap = Bootstrap(cityAi)

# Config for SQLite database
# cityAi.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///city_u.db'
cityAi.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False     
cityAi.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:\\Users\\jibre\\OneDrive\\Desktop\\cityAi\\instance\\city_u.db'
cityAi.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"connect_args": {"timeout": 15}}


# Initialize SQLAlchemy
db = SQLAlchemy(cityAi)

 

# Database Model
class Query(db.Model):
    __tablename__ = 'queries'

    id = db.Column(db.Integer, primary_key=True)
    query_text = db.Column(db.String(200), nullable=False)  # The action/query name
    response_text = db.Column(db.String(500), nullable=False)  # Text to be spoken
    url = db.Column(db.String(500), nullable=True)  # Optional URL to open
    language = db.Column(db.String(2), nullable=False)  # Language code ('en', 'ar', 'ms')

    def __repr__(self):
        return f"<Query {self.query_text}>"

# Create the database and the table
with cityAi.app_context():
    db.create_all()

# Create the database and the table
with cityAi.app_context():
    try:
        db.create_all()
        print("Database and table created successfully.")
    except Exception as e:
        print(f"Error creating database: {e}")

# Seed database with predefined queries
def seed_queries():
    queries = [
        {
            'query_text': 'welcome_message',
            'response_text': 'Hello, I am City U, your voice assistant from City University. Please choose a language.',
            'url': None,
            'language': 'en'
        },
        {
            'query_text': 'register_message',
            'response_text': 'Our intakes started in January, May, and September. Make sure to write your name and your information correctly.',
            'url': None,
            'language': 'en'
        },
        {
            'query_text': 'query_english',
            'response_text': 'Please choose a category.',
            'url': None,
            'language': 'en'
        },
        {
            'query_text': 'start_query_register',
            'response_text': 'Please choose a degree.',
            'url': None,
            'language': 'en'
        },
        {
            'query_text': 'start_query_locations',
            'response_text': 'Please choose a location.',
            'url': None,
            'language': 'en'
        },
        {
            'query_text': 'foundation',
            'response_text': 'City University Foundation Programme is an intensive one-year programme designed to prepare students for a degree in the field of study of their choice.',
            'url': 'https://city.edu.my/all-programmes/foundation/',
            'language': 'en'
        },
        {
            'query_text': 'handle_tell_me_more',
            'response_text': 'In this page you can know more about Malaysia and City u',
            'url': None,
            'language': 'en'
        },
         {
            'query_text': 'handle_contact',
            'response_text': 'You can contact the administration and send a WhatsApp to 00 6011-1326 6255 or email us at ug@city.edu.my.',
            'url': 'https://city.edu.my/about/contact-us/',
            'language': 'en'
        },
        {
            'query_text': 'Anything else',
            'response_text': 'Anything else?.',
            'url': None,
            'language': 'en'
        },
        {
            'query_text': 'arabic',
            'response_text': 'أهلا بك ، كيف يمكنني مساعدتك؟',
            'url': None,
            'language': 'ar'
        },
        {
            'query_text': 'start_query_register_arabic',
            'response_text': 'الرجاء اختيار الدرجة العلميه',
            'url': None,
            'language': 'ar'
        },
        {
            'query_text': 'handle_tell_me_more_arabic',
            'response_text': 'بدأت جامعة سيتي في عام 1984. لدينا مجموعة متنوعة من البرامج: التأسيس، الدبلوم، البكالوريوس، الماجستير، الدكتوراه  ودورات اللغة. هل هناك أي برنامج أنت مهتم به؟',
            'url': 'https://city.edu.my/apply-now/',
            'language': 'ar'
        },
        {
            'query_text': 'start_query_malay',
            'response_text': 'Sila pilih kategori ',
            'url': None,
            'language': 'ms'
        },
        {
            'query_text': 'start_query_register_malay',
            'response_text': 'Sila pilih ijazah ',
            'url': None,
            'language': 'ms'
        },
        {
            'query_text': 'handle_tell_me_more_malay',
            'response_text': ' City University dimulakan pada tahun seribu lapan ratus sembilan puluh empat. Kami mempunyai pelbagai program: Asasi, Diploma, Sarjana Muda, Sarjana, Doctor Falsafah, Kursus Bahasa. Adakah terdapat mana-mana program yang anda minati? ',
            'url': 'https://city.edu.my/apply-now/',
            'language': 'ms'
        }
    ]

  
    with cityAi.app_context():
        try:
            for query_data in queries:
                existing_query = Query.query.filter_by(query_text=query_data['query_text']).first()
                if not existing_query:
                    db.session.add(Query(**query_data))  # Use unpacking for cleaner code
            db.session.commit()
            print("Queries seeded successfully without duplicates.")
        except Exception as e:
            db.session.rollback()
            print(f"Error seeding database: {e}")

# Seed the queries
seed_queries()

# Speak function to fetch and speak response from database
def speak_from_db(query_text):
    try:
        query = Query.query.filter_by(query_text=query_text).first()
        if query:
            speak(query.response_text)  # Replace with your speak implementation
            if query.url:
                webbrowser.open(query.url)  # Open URL if available
        else:
            print(f"No query found for: {query_text}")
    except Exception as e:
        print(f"Error fetching query from database: {e}")

# open web page languages

@cityAi.route("/")
def language_page():

      return render_template("language.html")


@cityAi.route("/start-query")
def start_query():
    # start_handle_query()
    speak_from_db("welcome_message") 
    # speak("Hello, I am City U, your voice assistant from City University. Please choose a language ")
    return jsonify({"message": "Query handling started"})


# open web page english

@cityAi.route("/templates/english.html")
def english():
    # speak ( "Welcome to City U Assistant. How can I assist you today?")  # Define text here
    # speak(text, language='en')  # Pass the text and language to speak()
    return render_template("english.html")
   
           

@cityAi.route("/start_query")
def start_query_english():
    # speak("Please choose a category ")
    speak_from_db("query_english") 

    # handle_query()
    # return jsonify({"message": "Query handling started"})
    return render_template("english.html")


@cityAi.route('/process_query', methods=['POST'])
def process_query():
    query = request.json['query']
    return jsonify({'response': 'Your response here'})


# open web page register - english


@cityAi.route("/templates/register.html")
def register():
    return render_template("register.html")
   

            
@cityAi.route("/start_query_register")
def start_query_register():
    # speak("Please choose a degree ")
    speak_from_db("start_query_register") 

    # return jsonify({"message": "Query handling started"})
    return render_template("english.html")



# open web page location - english


@cityAi.route("/templates/locations.html")
def locations():
    return render_template("locations.html")
   


@cityAi.route("/start_query_locations")
def start_query_locations():
    # speak("Please choose a location ")
    speak_from_db("start_query_locations") 
    return render_template("english.html")
 




def handle_query(query):
     
    uni_type = recognize_speech_from_mic().get("transcription", "").lower()
    if uni_type:

        if 'register' in query or 'enroll' in query or 'sign up' in query or 'registration' in query:
            handle_register()

        elif 'programme' in query or 'course' in query or 'class' in query:
            handle_programme_request()

        elif 'english' in query or 'language' in query:
            handle_english()

        elif 'tell me ' in query or 'details' in query or 'more' in query or 'information' in query:
            handle_tell_me_more()

        elif 'contact ' in query or 'reach ' in query or 'get in touch ' in query:
            handle_contact()

        elif 'location' in query or 'where' in query or 'address' in query:
            handle_location()

        elif 'social media' in query or 'instagram' in query or 'social' in query:
            handle_social_media()

        else:
            speak(
                "I'm sorry, I can tell you more about City U and help with registration, "
                "programmes, courses. How can I assist you today?"
            )
    else:
            speak(
                "I'm sorry, I can tell you more about City U and help with registration, "
                "programmes, courses. How can I assist you today?"
            )        



# Functions to handle specific queries

# register

# @cityAi.route("/handle_register", methods=["POST"])
def handle_register():
    # speak(
    #     "What kind of program are you interested in? Foundation, Diploma, Bachelor's, "
    #     "Master's, PhD, Language Courses, or Executive Programmes?"
    # )
    register_type = recognize_speech_from_mic().get("transcription", "").lower()
    if register_type:
        speak(
            "Our intakes started in January, May, and September. Make sure to write your name "
            "and your information correctly so you can reserve your spot in the university and "
            "start your journey with City University."
        )
        if 'foundation' in register_type:
            # webbrowser.open("https://city.edu.my/all-programmes/foundation/")
            speak_from_db("foundation") 

            speak(
                "City University Foundation Programme is an intensive one-year programme designed to prepare students for a degree in the field of study of their choice."
            )
        elif 'diploma' in register_type:
            speak("City University Diploma Programme is an intensive one to two years programme.")
            webbrowser.open("https://city.edu.my/all-programmes/diploma/")
        elif 'bachelor' in register_type or 'undergraduate' in register_type:
            speak("City University Bachelor Programme is an intensive three to four years programme.")
            webbrowser.open("https://city.edu.my/all-programmes/bachelor/")
        elif 'master' in register_type or 'postgraduate' in register_type:
            speak("City University Master Programme is an intensive one to two years programme.")
            webbrowser.open("https://city.edu.my/all-programmes/masters-phd/")
        elif 'phd' in register_type or 'doctorate' in register_type:
            speak("City University PhD Programme is an intensive three to four years programme.")
            webbrowser.open("https://city.edu.my/all-programmes/masters-phd/")
        elif 'language' in register_type:
            speak("City University offers a variety of language courses.")
            webbrowser.open("https://city.edu.my/programme/language-course/general-intensive-english-programme/")
        elif 'executive' in register_type:
            speak("City University offers various executive programmes.")
            webbrowser.open("https://city.edu.my/all-programmes/continuing-education/")
        else:
            speak("Sorry, I didn't catch that. Please visit our university website for more information.")
            webbrowser.open("https://city.edu.my/all-programmes/")
    else:
        speak("Sorry, I didn't catch that. Please visit our university website for more information.")
        webbrowser.open("https://city.edu.my/all-programmes/")

    return render_template("english.html")


# foundation


@cityAi.route("/templates/foundation.html", methods=['GET','POST'])
def handle_register_foundation():
    # webbrowser.open("https://city.edu.my/all-programmes/foundation/")

    speak(
        "City University Foundation Programme is an intensive one-year programme designed to prepare students for a degree in the field of study of their choice." )
    return render_template("foundation.html")

@cityAi.route("/handle_register_foundation_arts_communication", methods=["POST"])
def handle_register_foundation_arts_communication():
    webbrowser.open("https://city.edu.my/all-programmes/foundation/")

    speak(
        "City University Foundation Programme is an intensive one-year programme designed to prepare students for a degree in the field of study of their choice." )
    # return render_template("english.html")

@cityAi.route("/handle_register_foundation_GRAPHIC_DESIGN_MULTIMEDIA", methods=["POST"])
def handle_register_foundation_GRAPHIC_DESIGN_MULTIMEDIA():
    webbrowser.open("https://city.edu.my/all-programmes/foundation/")

    speak(
        "City University Foundation Programme is an intensive one-year programme designed to prepare students for a degree in the field of study of their choice." )
    # return render_template("english.html")
    
    
@cityAi.route("/handle_register_foundation_FASHION_DESIGN", methods=["POST"])
def handle_register_foundation_FASHION_DESIGN():
    webbrowser.open("https://city.edu.my/all-programmes/foundation/")

    speak(
        "City University Foundation Programme is an intensive one-year programme designed to prepare students for a degree in the field of study of their choice." )
    # return render_template("english.html")


@cityAi.route("/handle_register_foundation_ENGLISH", methods=["POST"])
def handle_register_foundation_ENGLISH():
    webbrowser.open("https://city.edu.my/all-programmes/foundation/")

    speak(
        "City University Foundation Programme is an intensive one-year programme designed to prepare students for a degree in the field of study of their choice." )
    # return render_template("english.html")

@cityAi.route("/handle_register_foundation_BUILT_ENVIRONMENT", methods=["POST"])
def handle_register_foundation_BUILT_ENVIRONMENT():
    webbrowser.open("https://city.edu.my/all-programmes/foundation/")

    speak(
        "City University Foundation Programme is an intensive one-year programme designed to prepare students for a degree in the field of study of their choice." )
    # return render_template("english.html")
    
    
@cityAi.route("/handle_register_foundation_LIFE_SCIENCE", methods=["POST"])
def handle_register_foundation_LIFE_SCIENCE():
    webbrowser.open("https://city.edu.my/all-programmes/foundation/")

    speak(
        "City University Foundation Programme is an intensive one-year programme designed to prepare students for a degree in the field of study of their choice." )
    # return render_template("english.html")   
    
@cityAi.route("/handle_register_foundation_PHYSICAL_SCIENCE", methods=["POST"])
def handle_register_foundation_PHYSICAL_SCIENCE():
    webbrowser.open("https://city.edu.my/all-programmes/foundation/")

    speak(
        "City University Foundation Programme is an intensive one-year programme designed to prepare students for a degree in the field of study of their choice." )
    # return render_template("english.html")      
    
@cityAi.route("/handle_register_foundation_FOUNDATION_IN_BUSINESS", methods=["POST"])
def handle_register_foundation_FOUNDATION_IN_BUSINESS():
    webbrowser.open("https://city.edu.my/all-programmes/foundation/")

    speak(
        "City University Foundation Programme is an intensive one-year programme designed to prepare students for a degree in the field of study of their choice." )
    # return render_template("english.html")       
  
 
@cityAi.route("/handle_register_foundation_FOUNDATION_IN_IT", methods=["POST"])
def handle_register_foundation_FOUNDATION_IN_IT():
    webbrowser.open("https://city.edu.my/all-programmes/foundation/")

    speak(
        "City University Foundation Programme is an intensive one-year programme designed to prepare students for a degree in the field of study of their choice." )
    # return render_template("english.html") 
    
    
        
# diploma


@cityAi.route("/templates/diploma.html", methods=['GET','POST'])
def handle_register_diploma():
    # webbrowser.open("https://city.edu.my/all-programmes/diploma/")
    # speak("City University Diploma Programme is an intensive one to two years programme.")
    return render_template('diploma.html')

@cityAi.route("/start_query_register_diploma")
def start_query_register_diploma():
    speak("Please choose a major in Diploma   ")
    # return jsonify({"message": "Query handling started"})
    return render_template("diploma.html")







# bachelor


@cityAi.route("/templates/bachelor.html", methods=['GET','POST'])
def handle_register_bachelor():
    # webbrowser.open("https://city.edu.my/all-programmes/bachelor/")
    speak("City University Bachelor Programme is an intensive three to four years programme.")

    return render_template("bachelor.html")

@cityAi.route("/handle_register_bachelor", methods=["POST"])
def handle_register_bachelor_major():
    # webbrowser.open("https://city.edu.my/all-programmes/bachelor/")
    speak("City University Bachelor Programme is an intensive three to four years programme.")

    # return render_template("english.html")


# Master


@cityAi.route("/templates/master.html", methods=['GET','POST'])
def handle_register_master():
    # webbrowser.open("https://city.edu.my/all-programmes/masters-phd/")
    speak("City University Master Programme is an intensive one to two years programme.")
    speak("Please choose a major in Masters   ")
    return render_template("master.html")


# phd



@cityAi.route("/templates/phd.html", methods=['GET','POST'])
def handle_register_phd():
    # webbrowser.open("https://city.edu.my/all-programmes/masters-phd/")
    speak("City University PhD Programme is an intensive three to four years programme.")
    return render_template("phd.html")





@cityAi.route("/handle_register_language", methods=["POST"])
def handle_register_language():   
    speak("City University offers a variety of language courses.")

    webbrowser.open("https://city.edu.my/programme/language-course/general-intensive-english-programme/")
    speak(
        "We also prepare for IELTS exams and more with experienced faculty and practical applications for academic and professional success."
    )
    return render_template("english.html")


@cityAi.route("/handle_register_executive", methods=["POST"])
def handle_register_executive():
    webbrowser.open("https://city.edu.my/all-programmes/continuing-education/")
    speak("City University offers various executive programmes.")
    return render_template("english.html")



# programmes

@cityAi.route("/handle_programme", methods=["POST"])
def handle_programme_request():
    speak("What course are you interested in?")
    course_query = recognize_speech_from_mic().get("transcription", "").lower()
    if course_query:
        speak(f"We offer a variety of courses in {course_query}. Here is our courses page.")
        webbrowser.open("https://city.edu.my/all-programmes/")
        speak("Anything else?")
    else:
        speak("Sorry, I didn't catch that. Please visit our courses page for more information.")
        webbrowser.open("https://city.edu.my/all-programmes/")

    return render_template("english.html")



# About page

@cityAi.route("/templates/about.html", methods=['GET','POST'])
def handle_tell_me_more():
        
    speak_from_db("handle_tell_me_more") 
    # speak( "In this page you can know more about Malaysia and City u" )
    
    return render_template("about.html")

@cityAi.route("/handle_tell_me_malaysia", methods=["POST"])
def handle_tell_me_malaysia():
    # speak(
    #     "City University started in 1984. We have a variety of programs: Foundation, Diploma, Bachelor's, Master's, PhD, Language Courses. Is there any program that you are interested in?"
    # )
    # webbrowser.open("https://city.edu.my/apply-now/")
    # speak(
    #     "City University started in 1984. We have a variety of programs: Foundation, Diploma, Bachelor's, Master's, PhD and Language Courses. Is there any program that you are interested in?"
    # )
    # speak(
    #    "Our intakes started in January, May, and September. Make sure to write your name "
    #     "and your information correctly so you can reserve your spot in the university and "
    #     "start your journey with City University."
    # )
    speak("Anything else?")
    return render_template("english.html")

@cityAi.route("/handle_tell_me_city_u", methods=["POST"])
def handle_tell_me_city_u():
    # speak(
    #     "City University started in 1984. We have a variety of programs: Foundation, Diploma, Bachelor's, Master's, PhD, Language Courses. Is there any program that you are interested in?"
    # )
    webbrowser.open("https://city.edu.my/apply-now/")
    speak(
        "City University started in 1984. We have a variety of programs: Foundation, Diploma, Bachelor's, Master's, PhD and Language Courses. Is there any program that you are interested in?"
    )
    speak(
       "Our intakes started in January, May, and September. Make sure to write your name "
        "and your information correctly so you can reserve your spot in the university and "
        "start your journey with City University."
    )
    speak("Anything else?")
    return render_template("english.html")

@cityAi.route("/handle_tell_me_visa", methods=["POST"])
def handle_tell_me_visa():
    # speak(
    #     "City University started in 1984. We have a variety of programs: Foundation, Diploma, Bachelor's, Master's, PhD, Language Courses. Is there any program that you are interested in?"
    # )
    # webbrowser.open("https://city.edu.my/apply-now/")
    # speak(
    #     "City University started in 1984. We have a variety of programs: Foundation, Diploma, Bachelor's, Master's, PhD and Language Courses. Is there any program that you are interested in?"
    # )
    # speak(
    #    "Our intakes started in January, May, and September. Make sure to write your name "
    #     "and your information correctly so you can reserve your spot in the university and "
    #     "start your journey with City University."
    # )
    speak("Anything else?")
    return render_template("english.html")

@cityAi.route("/handle_tell_me_hostel", methods=["POST"])
def handle_tell_me_hostel():
    # speak(
    #     "City University started in 1984. We have a variety of programs: Foundation, Diploma, Bachelor's, Master's, PhD, Language Courses. Is there any program that you are interested in?"
    # )
    # webbrowser.open("https://city.edu.my/apply-now/")
    # speak(
    #     "City University started in 1984. We have a variety of programs: Foundation, Diploma, Bachelor's, Master's, PhD and Language Courses. Is there any program that you are interested in?"
    # )
    # speak(
    #    "Our intakes started in January, May, and September. Make sure to write your name "
    #     "and your information correctly so you can reserve your spot in the university and "
    #     "start your journey with City University."
    # )
    speak("Anything else?")
    return render_template("english.html")








@cityAi.route("/handle_english", methods=["POST"])
def handle_english():
    speak(
        "Excellent. Our English program at City University offers comprehensive courses to master the language."
    )
    webbrowser.open("https://city.edu.my/all-programmes/")
    speak(
        "We also prepare for IELTS exams and more with experienced faculty and practical applications for academic and professional success."
    )
    speak("You can send a WhatsApp at 0060173911812 or email us at language@city.edu.my.")
    speak("Anything else?")
    return render_template("english.html")

@cityAi.route("/handle_contact", methods=["POST"])
def handle_contact():
   
    speak_from_db("handle_contact") 
    
    # speak(
    #     "You can contact the administration and send a WhatsApp to 00 6011-1326 6255 or email us at ug@city.edu.my."
    # )
    # webbrowser.open("https://city.edu.my/contact-us/")
   
    # speak("Anything else?")
    return render_template("english.html")



# locatines

@cityAi.route("/handle_location", methods=["POST"])
def handle_location():
    speak("Choose your location")
    # webbrowser.open("https://maps.app.goo.gl/GWc5Qqi8uSqCRMDw5")
    # speak("Anything else?")
    # return render_template("english.html")



@cityAi.route("/handle_location_pj", methods=["POST"])
def handle_location_pj():
    speak("Opening our location in Google Maps in Patling Jaya.")
    webbrowser.open("https://maps.app.goo.gl/GWc5Qqi8uSqCRMDw5")
    speak("Anything else?")
    return render_template("english.html")

@cityAi.route("/handle_location_cyber", methods=["POST"])
def handle_location_cyber():
    speak("Opening our location in Google Maps in Cyberjaya.")
    webbrowser.open("https://maps.app.goo.gl/GWc5Qqi8uSqCRMDw5")
    speak("Anything else?")
    return render_template("english.html")




# social media

@cityAi.route("/templates/social.html", methods=['GET','POST'])
def handle_social_media():
    speak("Opening our Social media pages.")
    return render_template("social.html")



@cityAi.route("/handle_social_media_instagram", methods=["POST"])
def handle_social_media_instagram():
    speak("Opening our Instagram page.")
    webbrowser.open("https://www.instagram.com/city.university.malaysia/")
    speak("Anything else?")
    return render_template("english.html")

@cityAi.route("/handle_LMS", methods=["POST"])
def handle_LMS():
    speak("Opening our LMS page.")
    webbrowser.open("https://www.cityulms.com/Account/CityLogin.aspx")
    speak("Anything else?")
    return render_template("english.html")








# Arabic page 

 # open web page arabic

@cityAi.route("/templates/arabic.html")
def arabic():
    # text = "أهلا بك ، كيف يمكنني مساعدتك "  
    # speak_gtts("أهلا بك ، كيف يمكنني مساعدتك؟", language='ar')
   
    # speak_from_db("arabic") 
    speak("أهلا بك ، كيف يمكنني مساعدتك؟", language='ar')
    return render_template("arabic.html")

@cityAi.route("/start_query_arabic")
def start_query_arabic():
    # speak_gtts("أهلا بك ، كيف يمكنني مساعدتك ", language='ar')
    # handle_query()
    # return jsonify({"message": "Query handling started"})
    return render_template("arabic.html")


# open web page register - arabic


@cityAi.route("/templates/register_arabic.html")
def register_arabic():
    return render_template("register_arabic.html")
   


@cityAi.route("/start_query_register_arabic")
def start_query_register_arabic():
  
    # speak_from_db("start_query_register_arabic") 
    speak("الرجاء اختيار الدرجة العلميه", language='ar')
    # return jsonify({"message": "Query handling started"})
    return render_template("register_arabic.html")



def handle_query_arabic(query):
     
    uni_type = recognize_speech_from_mic().get("transcription", "").lower()
    if uni_type:

        if 'register' in query or 'enroll' in query or 'sign up' in query or 'registration' in query:
            handle_register()

        elif 'programme' in query or 'course' in query or 'class' in query:
            handle_programme_request()

        elif 'english' in query or 'language' in query:
            handle_english()

        elif 'tell me ' in query or 'details' in query or 'more' in query or 'information' in query:
            handle_tell_me_more()

        elif 'contact ' in query or 'reach ' in query or 'get in touch ' in query:
            handle_contact()

        elif 'location' in query or 'where' in query or 'address' in query:
            handle_location()

        elif 'social media' in query or 'instagram' in query or 'social' in query:
            handle_social_media()

        else:
            speak(
                "I'm sorry, I can tell you more about City U and help with registration, "
                "programmes, courses. How can I assist you today?"
            )
    else:
            speak(
                "I'm sorry, I can tell you more about City U and help with registration, "
                "programmes, courses. How can I assist you today?"
            )        



# Functions to handle specific queries

# register

@cityAi.route("/handle_register_arabic", methods=["POST"])
def handle_register_arabic():
    # speak(
    #     "What kind of program are you interested in? Foundation, Diploma, Bachelor's, "
    #     "Master's, PhD, Language Courses, or Executive Programmes?" )
    register_type = recognize_speech_from_mic().get("transcription", "").lower()
    if register_type:
        speak(
            "تبدأ دوراتنا في يناير ومايو وسبتمبر. تأكد من كتابة اسمك ومعلوماتك بشكل صحيح حتى تتمكن من حجز مقعدك في الجامعة وبدء رحلتك مع جامعة سيتي.", language='ar' )
        if 'foundation' in register_type:
            webbrowser.open("https://city.edu.my/all-programmes/foundation/")
            speak(
                "برنامج التآسيس في جامعة سيتي هو برنامج مكثف لمدة عام واحد مصمم لإعداد الطلاب للحصول على درجة علمية في مجال الدراسة التي يختارونها."
            , language='ar')
        elif 'diploma' in register_type:
            speak("برنامج دبلوم جامعة سيتي هو برنامج مكثف لمدة سنة إلى سنتين.", language='ar')
            webbrowser.open("https://city.edu.my/all-programmes/diploma/")
        elif 'bachelor' in register_type or 'undergraduate' in register_type:
            speak("City University Bachelor Programme is an intensive three to four years programme.")
            webbrowser.open("https://city.edu.my/all-programmes/bachelor/")
        elif 'master' in register_type or 'postgraduate' in register_type:
            speak("City University Master Programme is an intensive one to two years programme.")
            webbrowser.open("https://city.edu.my/all-programmes/masters-phd/")
        elif 'phd' in register_type or 'doctorate' in register_type:
            speak("City University PhD Programme is an intensive three to four years programme.")
            webbrowser.open("https://city.edu.my/all-programmes/masters-phd/")
        elif 'language' in register_type:
            speak("City University offers a variety of language courses.")
            webbrowser.open("https://city.edu.my/programme/language-course/general-intensive-english-programme/")
        elif 'executive' in register_type:
            speak("City University offers various executive programmes.")
            webbrowser.open("https://city.edu.my/all-programmes/continuing-education/")
        else:
            speak("Sorry, I didn't catch that. Please visit our university website for more information.")
            webbrowser.open("https://city.edu.my/all-programmes/")
    else:
        speak("Sorry, I didn't catch that. Please visit our university website for more information.")
        webbrowser.open("https://city.edu.my/all-programmes/")

    return render_template("arabic.html")

@cityAi.route("/handle_register_foundation_arabic", methods=["POST"])
def handle_register_foundation_arabic():
    webbrowser.open("https://city.edu.my/all-programmes/foundation/")

    speak(
        "برنامج التآسيس في جامعة سيتي هو برنامج مكثف لمدة عام واحد مصمم لإعداد الطلاب للحصول على الدرجة العلمية في مجال الدراسة التي يختارونها.", language='ar')
    return render_template("arabic.html")


@cityAi.route("/handle_register_diploma_arabic", methods=["POST"])
def handle_register_diploma_arabic():
    webbrowser.open("https://city.edu.my/all-programmes/diploma/")
    speak("برنامج دبلوم جامعة سيتي هو برنامج مكثف لمدة سنة إلى سنتين.", language='ar')
    return render_template("arabic.html")


@cityAi.route("/handle_register_bachelor_arabic", methods=["POST"])
def handle_register_bachelor_arabic():
    webbrowser.open("https://city.edu.my/all-programmes/bachelor/")
    speak("City University Bachelor Programme is an intensive three to four years programme.")
    return render_template("english.html")


@cityAi.route("/handle_register_master_arabic", methods=["POST"])
def handle_register_master_arabic():
    webbrowser.open("https://city.edu.my/all-programmes/masters-phd/")
    speak("City University Master Programme is an intensive one to two years programme.")
    return render_template("english.html")

@cityAi.route("/handle_register_phd_arabic", methods=["POST"])
def handle_register_phd_arabic():
    webbrowser.open("https://city.edu.my/all-programmes/masters-phd/")
    speak("City University PhD Programme is an intensive three to four years programme.")
    return render_template("english.html")


@cityAi.route("/handle_register_language_arabic", methods=["POST"])
def handle_register_language_arabic():   
    speak("City University offers a variety of language courses.")

    webbrowser.open("https://city.edu.my/programme/language-course/general-intensive-english-programme/")
    speak(
        "We also prepare for IELTS exams and more with experienced faculty and practical applications for academic and professional success."
    )
    return render_template("english.html")


@cityAi.route("/handle_register_executive_arabic", methods=["POST"])
def handle_register_executive_arabic():
    webbrowser.open("https://city.edu.my/all-programmes/continuing-education/")
    speak("City University offers various executive programmes.")
    return render_template("english.html")



# programmes

@cityAi.route("/handle_programme_arabic", methods=["POST"])
def handle_programme_request_arabic():
    speak("ما هو التخصص الذي انت مهتم به")
    course_query = recognize_speech_from_mic().get("transcription", "").lower()
    if course_query:
        speak(f"نحن نعرض العديد من التخصصات {course_query}. ها هي صفحه التخصصات", language='ar')
        webbrowser.open("https://city.edu.my/all-programmes/")
        speak("آي شئ اخر", language='ar')
    else:
        speak("آسف، لم أفهم ذلك. يرجى زيارة صفحة دوراتنا للحصول على المزيد من المعلومات", language='ar')
        webbrowser.open("https://city.edu.my/all-programmes/")
    speak("آي شئ اخر", language='ar')

    return render_template("english.html")


@cityAi.route("/handle_tell_me_more_arabic", methods=["POST"])
def handle_tell_me_more_arabic():
    # speak(
    #     "City University started in 1984. We have a variety of programs: Foundation, Diploma, Bachelor's, Master's, PhD, Language Courses. Is there any program that you are interested in?"
    # )
   

    # speak_from_db("handle_tell_me_more_arabic") 
    webbrowser.open("https://city.edu.my/apply-now/")
    speak(
        "بدأت جامعة سيتي في عام 1984. لدينا مجموعة متنوعة من البرامج: التأسيس، الدبلوم، البكالوريوس، الماجستير، الدكتوراه  ودورات اللغة. هل هناك أي برنامج أنت مهتم به؟"
    , language='ar')
    speak(
        "تبدآ دوراتنا في يناير ومايو وسبتمبر. تأكد من كتابة اسمك ومعلوماتك بشكل صحيح حتى تتمكن من حجز مقعدك في الجامعة وابدأ رحلتك مع جامعة سيتي", language='ar')
    speak("آي شئ اخر", language='ar')

    return render_template("arabic.html")

@cityAi.route("/handle_contact_arabic", methods=["POST"])
def handle_contact_arabic():
    speak(
        "يمكنك التواصل مع الإدارة وإرسال رسالة WhatsApp إلى 00 6011-1326 6255 أو مراسلتنا عبر البريد الإلكتروني على ug@city.edu.my.", language='ar')
    webbrowser.open("https://city.edu.my/about/contact-us/")
    speak("آي شئ اخر", language='ar')
    return render_template("arabic.html")

@cityAi.route("/handle_english_arabic", methods=["POST"])
def handle_english_arabic():
    speak(
        "ممتاز. يقدم برنامجنا للغة الإنجليزية في جامعة سيتي دورات شاملة لإتقان اللغة"
    , language='ar')
    webbrowser.open("https://city.edu.my/all-programmes/")
    speak(
        "نحن أيضًا نساعدك لتستعد لامتحانات IELTS  . وأعضاء هيئة تدريس ذوي خبرة وتطبيقات عملية للنجاح الأكاديمي والمهني."
    , language='ar')
    speak("يمكنك إرسال رسالة WhatsApp على الرقم 0060173911812 أو مراسلتنا عبر البريد الإلكتروني على language@city.edu.my")
    speak("آي شئ اخر", language='ar')
    return render_template("arabic.html")





# locatines

@cityAi.route("/handle_location_arabic", methods=["POST"])
def handle_location_arabic():
    speak("الرجاء اختيار الموقع", language='ar')
    # webbrowser.open("https://maps.app.goo.gl/GWc5Qqi8uSqCRMDw5")
    # speak("Anything else?")
    # return render_template("english.html")



@cityAi.route("/handle_location_pj_arabic", methods=["POST"])
def handle_location_pj_arabic():
    speak("تفضل موقعنا على خرائط جوجل في باتالينج جايا.", language='ar')
    webbrowser.open("https://maps.app.goo.gl/GWc5Qqi8uSqCRMDw5")
    speak("آي شئ اخر", language='ar')
    return render_template("arabic.html")

@cityAi.route("/handle_location_cyber_arabic", methods=["POST"])
def handle_location_cyber_arabic():
    speak("تفضل موقعنا على خرائط جوجل في سايبرجايا.", language='ar')
    webbrowser.open("https://maps.app.goo.gl/GWc5Qqi8uSqCRMDw5")
    speak("آي شئ اخر", language='ar')
    return render_template("arabic.html")


# @cityAi.route("/handle_location", methods=["POST"])
# def handle_register_bachelor():





@cityAi.route("/handle_social_media_arabic", methods=["POST"])
def handle_social_media_arabic():
    speak("تفضل صفحتنا في الانستقرام", language='ar')
    webbrowser.open("https://www.instagram.com/city.university.malaysia/")
    speak("آي شئ اخر", language='ar')
    return render_template("arabic.html")

@cityAi.route("/handle_LMS_arabic", methods=["POST"])
def handle_LMS_arabic():
    speak("تفضل صفحتنا  LMS", language='ar')
    webbrowser.open("https://www.cityulms.com/Account/CityLogin.aspx")
    speak("آي شئ اخر", language='ar')
    return render_template("arabic.html")


# Malay page 

 # open web page malay

@cityAi.route("/templates/malay.html")
def malay():
    return render_template("malay.html")

@cityAi.route("/start_query_malay")
def start_query_malay():

    # speak_from_db("start_query_malay") 
    speak("Sila pilih kategori ", language='ms')
    # speak_gtts("Sila pilih kategori", language='ms')

    # handle_query_malay()
    # return jsonify({"message": "Query handling started"})
    return render_template("malay.html")


# open web page register - malay


@cityAi.route("/templates/register_malay.html")
def register_malay():
    # speak(text, language='ms')  # Speak in Malay
    return render_template("register_malay.html")
   


@cityAi.route("/start_query_register_malay")
def start_query_register_malay():
    speak("Sila pilih ijazah", language='ms')
   
    # speak_from_db("start_query_register_malay") 
    # return jsonify({"message": "Query handling started"})
    return render_template("malay.html")



def handle_query_malay(query):
     
    uni_type = recognize_speech_from_mic().get("transcription", "").lower()
    if uni_type:

        if 'register' in query or 'enroll' in query or 'sign up' in query or 'registration' in query:
            handle_register_malay()

        elif 'programme' in query or 'course' in query or 'class' in query:
            handle_programme_request_malay()

        elif 'english' in query or 'language' in query:
            handle_english_malay()

        elif 'tell me ' in query or 'details' in query or 'more' in query or 'information' in query:
            handle_tell_me_more_malay()

        elif 'contact ' in query or 'reach ' in query or 'get in touch ' in query:
            handle_contact_malay()

        elif 'location' in query or 'where' in query or 'address' in query:
            handle_location_malay()

        elif 'social media' in query or 'instagram' in query or 'social' in query:
            handle_social_media_malay()

        else:
            speak(
                "I'm sorry, I can tell you more about City U and help with registration, "
                "programmes, courses. How can I assist you today?"
            )
    else:
            speak(
                "I'm sorry, I can tell you more about City U and help with registration, "
                "programmes, courses. How can I assist you today?"
            )        



# Functions to handle specific queries

# register

@cityAi.route("/handle_register_malay", methods=["POST"])
def handle_register_malay():
  
    speak("Program jenis apa yang anda minati?" , language='ms')
  
    # speak(
    #     "What kind of program are you interested in? Foundation, Diploma, Bachelor's, "
    #     "Master's, PhD, Language Courses, or Executive Programmes?" )
    register_type = recognize_speech_from_mic().get("transcription", "").lower()
    if register_type:
        speak(
            "Pengambilan kami bermula pada bulan Januari, Mei, dan September. Pastikan anda menulis nama dan maklumat anda dengan betul supaya anda boleh menempah tempat anda di universiti dan memulakan perjalanan anda dengan City University."
        , language='ms')
        if 'foundation' in register_type:
            webbrowser.open("https://city.edu.my/all-programmes/foundation/")
            speak(
                "City University Foundation Programme is an intensive one-year programme designed to prepare students for a degree in the field of study of their choice."
            )
        elif 'diploma' in register_type:
            speak("Program Diploma City University adalah program intensif selama satu hingga dua tahun.")
            webbrowser.open("https://city.edu.my/all-programmes/diploma/")
        elif 'bachelor' in register_type or 'undergraduate' in register_type:
            speak("Program Sarjana Muda City University adalah program intensif selama tiga hingga empat tahun.")
            webbrowser.open("https://city.edu.my/all-programmes/bachelor/")
        elif 'master' in register_type or 'postgraduate' in register_type:
            speak("Program Sarjana City University adalah program intensif selama satu hingga dua tahun.")
            webbrowser.open("https://city.edu.my/all-programmes/masters-phd/")
        elif 'phd' in register_type or 'doctorate' in register_type:
            speak("City University PhD Programme is an intensive three to four years programme.")
            webbrowser.open("https://city.edu.my/all-programmes/masters-phd/")
        elif 'language' in register_type:
            speak("City University offers a variety of language courses.")
            webbrowser.open("https://city.edu.my/programme/language-course/general-intensive-english-programme/")
        elif 'executive' in register_type:
            speak("City University offers various executive programmes.")
            webbrowser.open("https://city.edu.my/all-programmes/continuing-education/")
        else:
            speak("Sorry, I didn't catch that. Please visit our university website for more information.")
            webbrowser.open("https://city.edu.my/all-programmes/")
    else:
        speak("Sorry, I didn't catch that. Please visit our university website for more information.")
        webbrowser.open("https://city.edu.my/all-programmes/")

    return render_template("malay.html")

@cityAi.route("/handle_register_foundation_malay", methods=["POST"])
def handle_register_foundation_malay():
    webbrowser.open("https://city.edu.my/all-programmes/foundation/")

    speak(
        "Program Asas Universiti City adalah program intensif selama satu tahun yang direka untuk menyediakan pelajar bagi melanjutkan pengajian dalam bidang pilihan mereka.", language='ms' )
    return render_template("malay.html")


@cityAi.route("/handle_register_diploma_malay", methods=["POST"])
def handle_register_diploma_malay():
    webbrowser.open("https://city.edu.my/all-programmes/diploma/")
    speak("Program Diploma Universiti City adalah program intensif selama satu hingga dua tahun.", language='ms')
    return render_template("malay.html")


@cityAi.route("/handle_register_bachelor_malay", methods=["POST"])
def handle_register_bachelor_malay():
    webbrowser.open("https://city.edu.my/all-programmes/bachelor/")
    speak("Program Sarjana Muda Universiti City adalah program intensif selama tiga hingga empat tahun.", language='ms')
    return render_template("malay.html")


@cityAi.route("/handle_register_master_malay", methods=["POST"])
def handle_register_master_malay():
    webbrowser.open("https://city.edu.my/all-programmes/masters-phd/")
    speak("Program Sarjana Universiti City adalah program intensif selama satu hingga dua tahun.", language='ms')
    return render_template("malay.html")

@cityAi.route("/handle_register_phd_malay", methods=["POST"])
def handle_register_phd_malay():
    webbrowser.open("https://city.edu.my/all-programmes/masters-phd/")
    speak("Program PhD Universiti City adalah program intensif selama tiga hingga empat tahun.", language='ms')
    return render_template("malay.html")


@cityAi.route("/handle_register_language_malay", methods=["POST"])
def handle_register_language_malay():   
    speak("Universiti City menawarkan pelbagai kursus bahasa." ,language='ms')

    webbrowser.open("https://city.edu.my/programme/language-course/general-intensive-english-programme/")
    speak(
        "Kami juga menyediakan persediaan untuk peperiksaan IELTS dan banyak lagi dengan tenaga pengajar berpengalaman serta aplikasi praktikal untuk kejayaan akademik dan profesional.",language='ms'
    )
    return render_template("malay.html")


@cityAi.route("/handle_register_executive_malay", methods=["POST"])
def handle_register_executive_malay():
    webbrowser.open("https://city.edu.my/all-programmes/continuing-education/")
    speak("City University menawarkan pelbagai program eksekutif.",language='ms')
    return render_template("malay.html")



# programmes

@cityAi.route("/handle_programme_malay", methods=["POST"])
def handle_programme_request_malay():
    speak("What course are you interested in?")
    course_query = recognize_speech_from_mic().get("transcription", "").lower()
    if course_query:
        speak(f"We offer a variety of courses in {course_query}. Here is our courses page.")
        webbrowser.open("https://city.edu.my/all-programmes/")
        speak("Anything else?")
    else:
        speak("Sorry, I didn't catch that. Please visit our courses page for more information.")
        webbrowser.open("https://city.edu.my/all-programmes/")
    speak("Ada apa-apa lagi?")

    return render_template("malay.html")


@cityAi.route("/handle_tell_me_more_malay", methods=["POST"])
def handle_tell_me_more_malay():
   
    # speak_from_db("handle_tell_me_more_malay") 
    speak(
        "City University dimulakan pada tahun seribu lapan ratus sembilan puluh empat. Kami mempunyai pelbagai program: Asasi, Diploma, Sarjana Muda, Sarjana, Doctor Falsafah, Kursus Bahasa. Adakah terdapat mana-mana program yang anda minati? " , language='ms'   )
    webbrowser.open("https://city.edu.my/apply-now/")

    speak(
        "Pengambilan kami bermula pada bulan Januari, Mei, dan September. Pastikan anda menulis nama dan maklumat anda dengan betul supaya anda boleh menempah tempat anda di universiti dan memulakan perjalanan anda dengan City University.", language='ms')
    speak("Ada apa-apa lagi?", language='ms')
    return render_template("malay.html")

@cityAi.route("/handle_english_malay", methods=["POST"])
def handle_english_malay():
    speak(
        "Program Bahasa Inggeris kami di City University menawarkan kursus komprehensif untuk menguasai bahasa tersebut."
   ,language='ms' )
    webbrowser.open("https://city.edu.my/all-programmes/")
    speak(
        "Kami juga menyediakan persediaan untuk peperiksaan IELTS dan lain-lain dengan tenaga pengajar berpengalaman serta aplikasi praktikal untuk kejayaan akademik dan profesional."
    , language='ms')
    speak("Anda boleh menghantar mesej WhatsApp ke 0060173911812 atau e-mel kami di language@city.edu.my.", language='ms')
    speak("Ada apa-apa lagi?", language='ms')
    return render_template("malay.html")

@cityAi.route("/handle_contact_malay", methods=["POST"])
def handle_contact_malay():
    speak(
        "Anda boleh menghubungi pihak pentadbiran dengan menghantar mesej WhatsApp ke 006011-1326 6255 atau e-mel kami di ug@city.edu.my."
   , language='ms' )
    webbrowser.open("https://city.edu.my/about/contact-us/")
    speak("Ada apa-apa lagi?", language='ms')
    return render_template("malay.html")



# locatines

@cityAi.route("/handle_location_malay", methods=["POST"])
def handle_location_malay():
    speak("Pilih lokasi anda" , language='ms')
    # webbrowser.open("https://maps.app.goo.gl/GWc5Qqi8uSqCRMDw5")
    # speak("Anything else?")
    # return render_template("english.html")



@cityAi.route("/handle_location_pj_malay", methods=["POST"])
def handle_location_pj_malay():
    speak("Membuka lokasi kami di Google Maps di Petaling Jaya.", language='ms')
    webbrowser.open("https://maps.app.goo.gl/GWc5Qqi8uSqCRMDw5")
    speak("Ada apa-apa lagi?", language='ms')
    return render_template("malay.html")

@cityAi.route("/handle_location_cyber_malay", methods=["POST"])
def handle_location_cyber_malay():
    speak("Membuka lokasi kami di Google Maps di Cyberjaya.", language='ms')
    webbrowser.open("https://maps.app.goo.gl/GWc5Qqi8uSqCRMDw5")
    speak("Ada apa-apa lagi?", language='ms')
    return render_template("malay.html")


# @cityAi.route("/handle_location", methods=["POST"])
# def handle_register_bachelor():


@cityAi.route("/handle_social_media_malay", methods=["POST"])
def handle_social_media_malay():
    speak("Membuka halaman Instagram kami", language='ms')
    webbrowser.open("https://www.instagram.com/city.university.malaysia/")
    speak("Ada apa-apa lagi?", language='ms')
    return render_template("malay.html")

@cityAi.route("/handle_LMS_malay", methods=["POST"])
def handle_LMS_malay():
    speak("Membuka halaman LMS kami", language='ms')
    webbrowser.open("https://www.cityulms.com/Account/CityLogin.aspx")
    speak("Ada apa-apa lagi?", language='ms')
    return render_template("malay.html")


if __name__ == "__main__":
    cityAi.run(debug=True, port=5001)  # Run the Flask development server

    # speak("Hello, I am City U, your voice assistant from City University. How can I assist you today?")
    while True:
        response = recognize_speech_from_mic()
        if response["success"]:
            query = response["transcription"].lower()
            # print("You said:", query)
           
            if 'Hi' in query or "Hey" in query or 'Hello' in query or "What's up?"in query or "Good day!" in query  :
                    speak(" Hello! what can I do for you?")
    
            elif 'exit' in query or 'bye' in query or 'thank you' in query:
                    speak("Goodbye! ave a nice day.")
                    break
            handle_query(query)
         
        else:
            print("Error:", response["error"])
            speak("Sorry, I didn't catch that.")         