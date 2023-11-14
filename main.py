#https://www.geeksforgeeks.org/python-imdbpy-searching-a-movie/
#https://stackoverflow.com/questions/151272/given-an-imdb-movie-id-how-do-i-programmatically-get-its-poster-image#:~:text=The%20best%20solution%20is%20to%20use%20tmdb.org%20%3A,you%20can%20use%20in%20an%20img%20tag%20%3A-%29
#https://stackoverflow.com/questions/7391945/how-do-i-read-image-data-from-a-url-in-python
#https://stackoverflow.com/questions/48919003/pandas-split-on-regex
#https://regex101.com/r/ECVDtm/2
#https://www.geeksforgeeks.org/python-imdbpy-searching-a-movie/
#https://stackoverflow.com/questions/151272/given-an-imdb-movie-id-how-do-i-programmatically-get-its-poster-image#:~:text=The%20best%20solution%20is%20to%20use%20tmdb.org%20%3A,you%20can%20use%20in%20an%20img%20tag%20%3A-%29
#https://stackoverflow.com/questions/7391945/how-do-i-read-image-data-from-a-url-in-python

from PIL import Image, ImageTk
import requests
from io import BytesIO
import tkinter as tk
import imdb
import pandas as pd
from tkinter import ttk
from functools import partial
import Levenshtein

# Create an instance of the IMDb class
#################### INIT RESOURCES ####################################
ia = imdb.Cinemagoer()
df = pd.read_csv('movies.csv')

df['year'] = df['title'].str.extract(r'\((\d{4})\)')
df['title'] = df['title'].str.extract(r'^(.*?) \(\d{4}\)')
df['title'] = df['title'].apply(lambda x: str(x))
df.dropna() 

#################### INIT GLOBAL VARS ####################################
displayed_movies = df.sample(n=10)

# initalize choices
user_choices_df = pd.DataFrame(columns=['title', 'year', 'genres', 'imdbId'])

# Initialize the main window
root = tk.Tk()
root.title("Movies Display")

# construct the overall form layout
movie_display_grid = ttk.Frame(root)
movie_display_grid.grid(row=0, column=0, columnspan=5)
user_controls_grid = ttk.Frame(root)
user_controls_grid.grid(row=1, column=0, columnspan=5)
user_choices_grid = ttk.Frame(root)
user_choices_grid.grid(row=2, column=0, columnspan=5)
search_window = None

#################### CINEAMAGOER QUERIES ####################################
def get_picture_and_rating_from_id(movie_id):
    movie = ia.get_movie(movie_id)
    cover_url = movie.get('cover url')
    rating = movie.get('rating')

    # Fetch the image from the cover URL
    response = requests.get(cover_url)
    img_data = response.content
    image = Image.open(BytesIO(img_data))
    photo = ImageTk.PhotoImage(image)
    return photo, rating

def get_rating_from_id(movie_id):
    movie = ia.get_movie(movie_id)
    return  movie.get('rating')

#################### KNEAREST SEARCH FUNCTIONS ####################################
def get_10_similar_to_list(list: pd.DataFrame):
    global df
    def weighted_jaccard_similarity(weighted_dictionary: dict, comparator_genres: str):
        # weighted_dictionary is based on all the selections that the user has made so far
        # comparator_genres is another movie's genres that is being compared
        numerator = 0
        denominator = weighted_dictionary['total']
        for genre in comparator_genres.split('|'):
            if genre in weighted_dictionary:
                numerator += weighted_dictionary[genre]

        return numerator / denominator
    
    def euclidean_distance(base_case_year: int, comparator_year: int):
        return abs(base_case_year - comparator_year)
    
    # followed from book, minor changes for type mismatch
    genres_weighted_dictionary = {'total': 0}
    for _, movie in list.iterrows():
        genres = movie['genres'].split('|')  # the genres are separated by a |
        for genre in genres: 
            if genre in genres_weighted_dictionary:
                genres_weighted_dictionary[genre] += 1
            else:
                genres_weighted_dictionary[genre] = 1
            genres_weighted_dictionary['total'] += 1

    df['weighted_jaccard_genres'] = df['genres'].map(lambda x: weighted_jaccard_similarity(genres_weighted_dictionary, x))

    # get year with euclidean distance
    list['year'] = list['year'].astype(int)
    avg_year = list['year'].mean() # this may be useless.... maybe i need to do a weighted_euclidiean?
    df['euclidean_year'] = df['year'].map(lambda x: euclidean_distance(int(avg_year), int(x)) if not pd.isna(x) else 0)

    #normalize euclidean_year
    min_value = df['euclidean_year'].min()
    max_value = df['euclidean_year'].max()
    df['euclidean_year'] = abs((df['euclidean_year'] - min_value) / (max_value - min_value) - 1)# x - min / max - min     0 - 1
    #TODO: this is exactly backwards.... TODO: fix this UPDATE: Fixed, by adding abs(<x> - 1)

    #apply weights and get absolute similarity
    df['absolute_similarity'] = df.apply(lambda x: x['weighted_jaccard_genres'] * 0.8 + x['euclidean_year'] * 0.2, axis='columns')
    # df['absolute_similarity'] = df.apply(lambda x: x['weighted_jaccard_genres'] * 0.02 + x['euclidean_year'] * 0.98, axis='columns')


    # sorted_df = df.sort_values(by='weighted_jaccard_genres', ascending=False)
    # sorted_df = df.sort_values(by='euclidean_year')
    sorted_df = df.sort_values(by='absolute_similarity', ascending=False)    
    return sorted_df.head(10) # K = 10

def get_10_similar_titles_from_df(comparison_value):
    # The following evaluates each movie with the given metric.
    # 'x' is the value in each row in the 'comparison_type' column
    # print(df.head())
    df['levenshtein'] = df["title"].map(lambda x: Levenshtein.distance(comparison_value, x))

    sorted_df = df.sort_values(by='levenshtein')
    # Get the top 10 similar titles
    return sorted_df.head(10)

#################### BUTTON FUNCTIONS AND FORM BEHAVIOR ####################################
def clear_user_choices():
    global user_choices_df
    user_choices_df = pd.DataFrame(columns=['title', 'year', 'genres', 'imdbId'])
    for widget in user_choices_grid.winfo_children():
        widget.destroy()

def nothing():
    print("nothing")

def get_movie_row_info(movie_row):
    id = movie_row['imdbId']
    title = movie_row['title']
    genres = movie_row['genres']
    year = movie_row['year']
    return id, title, year, genres

def add_choice(movie_row):
    global user_choices_df, user_choices_grid
    id, title, year, genres = get_movie_row_info(movie_row)
    
    if id in user_choices_df['imdbId'].values:
        return   

    choice = ttk.Label(user_choices_grid, text=title)
    choice.pack()
    # https://stackoverflow.com/questions/24284342/insert-a-row-to-pandas-dataframe
    new_row = {'title': title, 'year': year, 'genres': genres, 'imdbId': id} 
    new_row_df = pd.DataFrame([new_row])  
    user_choices_df = pd.concat([new_row_df, user_choices_df]).reset_index(drop=True)

def display_movies(movies):
    for widget in movie_display_grid.winfo_children():
        widget.destroy()
    for i in range(len(movies)):
        # Get the ID and details of the movie
        movie_details = movies.iloc[i]

        id, title, year, genres = get_movie_row_info(movie_details)
        description_text = f"Title: {title}\nYear: {year}\nGenres: {genres}"

        # Fetch and create the movie image
        photo = ""
        
        # photo, rating = get_picture_and_rating_from_id(id) ### COMMENT IN FOR IMAGE
        # description_text += f"\nRating: {rating}"          ### COMMENT IN FOR IMAGE

        # Create the image label
        image_button = ttk.Button(movie_display_grid, image=photo, command=partial(add_choice, movie_details))
        image_button.image = photo

        description_label = ttk.Label(movie_display_grid, text=description_text)

        image_button.grid(     row=i // 5 * 2,              column=i % 5, padx=10, pady=10)
        description_label.grid(row=i // 5 * 2 + 1,          column=i % 5)

def search():
    global search_window

    def perform_search():
        search_term = search_entry.get()
        print(f"Performing search for: {search_term}")

        search_results = get_10_similar_titles_from_df(search_term)

        search_result_frame = ttk.Frame(search_window)
        search_result_frame.grid(row=2, column=0)


        #display search options
        for i in range(len(search_results)):
            movie_details = search_results.iloc[i]

            id, title, year, genres = get_movie_row_info(movie_details)
            rating = 'DEBUG'            
            # rating = get_rating_from_id(id) ### COMMENT IN FOR IMAGE
            description_text = f"Title: {title}\nYear: {year}\nGenres: {genres}\nRating: {rating}"

            description_label = ttk.Label(search_result_frame, text=description_text)
            pick_button = ttk.Button(search_result_frame, text="pick", command=partial(add_choice, movie_details))

            description_label.grid( row=i // 5 * 2,              column=i % 5, padx=10, pady=10)
            pick_button.grid(       row=i // 5 * 2 + 1,          column=i % 5)


    # Check if the search_window exists
    if search_window is None or not search_window.winfo_exists():
        search_window = tk.Toplevel(root)
        search_window.title("Search")

    # create search popup and fill...
    search_entry_frame = ttk.Frame(search_window)

    search_prompt = ttk.Label(search_window, text="Enter the title of the movie to search for: ")
    search_entry = ttk.Entry(search_entry_frame, width=50)

    search_button = ttk.Button(search_entry_frame, text="Search", command=perform_search)

    search_prompt.grid(row=0, column=0)
    search_entry_frame.grid(row=1 ,columnspan=2)

    search_button.grid(row= 1, column=1,padx=10, pady=10)
    search_entry.grid(row=1, column=0, padx=10, pady=10)

def display_new():
    #insert recomendation
    displayed_movies = df.sample(n=10)
    display_movies(displayed_movies)

def debug():
    print("debug_btn called...")
    display_movies(get_10_similar_to_list(user_choices_df))

def display_recomended():
    display_movies(get_10_similar_to_list(user_choices_df))

#################### FILL FORM WITH BUTTONS ####################################
refresh_button = ttk.Button(user_controls_grid, text='Refresh Choices', command=display_new)
refresh_button.grid(row=0, column=0)
clear_user_choices_button = ttk.Button(user_controls_grid, text='Clear', command=clear_user_choices)
clear_user_choices_button.grid(row=0, column=1)
search_button = ttk.Button(user_controls_grid, text='Search', command=search)
search_button.grid(row=0, column=2)
debug_btn = ttk.Button(user_controls_grid, text='Debug', command=debug)
debug_btn.grid(row=0, column=10)
recomendation_display_button = ttk.Button(user_controls_grid, text='Display Recomended', command=display_recomended)
recomendation_display_button.grid(row=0, column=9)


#################### DISPLAY START ####################################
display_movies(displayed_movies)

#################### TKINTER MAIN LOOP ####################################
root.mainloop()