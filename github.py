import os
import requests
import json
from dotenv import load_dotenv
# from datetime import datetime


load_dotenv()  # load environment variables from .env file
sarahToken = os.getenv('sarahGithubToken')

headers = {'Authorization': f'token {sarahToken}',
           'Accept': 'application/vnd.github+json'} 

def check_rate_limit():
    response = requests.get('https://api.github.com/rate_limit', headers=headers)
    if response.status_code == 200:
        rate_limit_data = response.json()
        print(json.dumps(rate_limit_data, indent=4))
    else:
        print(f"Failed to retrieve rate limit data: {response.content}")

# check_rate_limit()
# reset_time = 1699582588  # replace with actual reset time
# reset_time_human_readable = datetime.utcfromtimestamp(reset_time).strftime('%Y-%m-%d %H:%M:%S')
# print(f"The rate limit will reset at: {reset_time_human_readable} UTC")

def get_popular_repos(language):
    url = f'https://api.github.com/search/repositories?q=language:{language}&sort=stars&order=desc'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['items']
    else:
        print(f'Failed to retrieve data: {response.content}')
        return None

def get_contributors(repo):
    url = f'https://api.github.com/repos/{repo}/contributors'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Failed to retrieve data: {response.content}')
        return None

def get_user_info(username):
    url = f'https://api.github.com/users/{username}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Failed to retrieve data: {response.content}')
        return None

# # TESTING FOR BEGINNING FUNCTIONS

# # Example usage for  replace JavaScript with whatever language
# popular_repos = get_popular_repos('JavaScript')
# print(json.dumps(popular_repos, indent=4))   

# # Example usage, replace JavaScript with whatever repo
# contributors = get_contributors('facebook/react')
# print(json.dumps(contributors, indent=4))

# # Example usage, replace alevol22 with whatever user
# user_info = get_user_info('alevol22')
# print(json.dumps(user_info, indent=4)) 

def search_users(language, min_followers, min_contributions, regions, headers):
    query = f'language:{language} followers:>={min_followers}'
    url = f'https://api.github.com/search/users?q={query}&sort=followers&order=desc'
    filtered_users = []

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            users = response.json().get('items', [])
            for user in users:
                user_info_url = f'https://api.github.com/users/{user["login"]}'
                user_response = requests.get(user_info_url, headers=headers)
                if user_response.status_code == 200:
                    user_info = user_response.json()
                    user_location = (user_info.get('location') or '').lower()
                    if any(region.lower() in user_location for region in regions):
                        contributions = get_total_user_contributions(user['login'], headers)
                        if contributions >= min_contributions:
                            filtered_users.append(user)
                else:
                    print(f'Failed to retrieve user info for user: {user["login"]}. Status Code: {user_response.status_code}')

            # Check for the 'next' page after processing current batch
            if 'next' in response.links:
                url = response.links['next']['url']
            else:
                url = None  # No more pages
        else:
            print(f'Failed to retrieve data: {response.content}')
            break  # Stop if there's an error

    return filtered_users

def get_total_user_contributions(username, headers):
    total_contributions = 0
    page = 1
    while True:
        repos_url = f'https://api.github.com/users/{username}/repos?page={page}&per_page=100'
        repos_response = requests.get(repos_url, headers=headers)
        if repos_response.status_code == 200:
            repos = repos_response.json()
            if not repos:
                break  # No more repositories to process
            for repo in repos:
                contributions_url = f'https://api.github.com/repos/{repo["full_name"]}/contributors'
                contributions_response = requests.get(contributions_url, headers=headers)
                if contributions_response.status_code == 200:
                    contributors = contributions_response.json()
                    for contributor in contributors:
                        if contributor['login'].lower() == username.lower():
                            total_contributions += contributor['contributions']
        else:
            print(f'Failed to retrieve repositories for user: {username}')
            break  # Stop if there's an error
        page += 1  # Go to the next page of repositories

    return total_contributions

def filter_users_by_region(users, regions):
    filtered_users = []
    for user in users:
        user_info_url = f'https://api.github.com/users/{user["login"]}'
        response = requests.get(user_info_url, headers=headers)
        if response.status_code == 200:
            user_info = response.json()
            user_location = (user_info.get('location') or '').lower()
            if any(region.lower() in user_location for region in regions):
                filtered_users.append(user)
        else:
            print(f'Failed to retrieve user info for user: {user["login"]}. Status Code: {response.status_code}')
    return filtered_users

# getting emails of a list of users
def get_user_email(username):
    url = f'https://api.github.com/users/{username}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        user_data = response.json()
        return user_data.get('email', 'n/a')  # Return the email if available, otherwise none
    else:
        print(f'Failed to retrieve data for {username}: {response.content}')
        return 'n/a'

# usernames = [
#     "eugenp", "cy6erGn0m", "androidbroadcast", "vitalets", "boriszv", "wegorich",
#     "victorrentea", "mohamed-taman", "marcingrzejszczak", "OlegDokuka", "luksa",
#     "barancev", "michalosman", "koral--", "johntakesnote", "rahmanusta", "asiekierka",
#     "angryziber", "PiotrMachowski", "AnghelLeonard", "pwittchen", "javadev", "armcha",
#     "zsmb13", "T8RIN", "alkanoidev", "rodion-gudz", "Smak80", "SpacingBat3", "pawegio",
#     "langara", "jkuri", "mrmlnc", "MichalLytek", "NickIliev", "ssleptsov", "filbabic",
#     "s-KaiNet", "akserg", "kbakdev", "adrianhajdin", "florinpop17", "LaravelDaily",
#     "BEPb", "mourner", "luxplanjay", "wojtekmaj", "filiphric", "Ahmad-Akel", "darjaorlova"
# ]


# user_emails = []

# # Iterate over each username and get their email
# for username in usernames:
#     email = get_user_email(username)
#     user_emails.append(email)

# # Print the emails
# for email in user_emails:
#     print(email)


# # ADVANCED FUNCTIONS TESTING

language = 'JavaScript'
min_followers = 50
min_stars = 100
min_contributions = 500

eastern_european_countries = [
    "Eastern Europe","Eastern European", "Russia", "Ukraine", "Poland", "Romania",
    "Czech Republic", "Hungary", "Belarus",
    "Bulgaria", "Slovakia", "Croatia", "Moldova",
    "Bosnia and Herzegovina", "Albania", "Lithuania",
    "North Macedonia", "Slovenia", "Latvia", "Estonia",
    "Montenegro", "Luxembourg", "Serbia", "Cyprus",
    "Azerbaijan", "Georgia", "Armenia", "Kosovo"
]

filtered_candidates = search_users(language, min_followers, min_contributions, eastern_european_countries, headers)

print(json.dumps(filtered_candidates, indent=4))