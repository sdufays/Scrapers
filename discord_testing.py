#Use tool to hire 3 Web Devs, 2-3 Platform Engineers (Kotlin and Node), and 1 Node/TS engineer for Audio Server.
import requests
import json
import re
import os
from dotenv import load_dotenv
import pandas as pd

# don't think this works though...
load_dotenv()  # load environment variables from .env file
githubToken = os.getenv('GITHUB_TOKEN')
discordKey = os.getenv('DISCORD_KEY')

# setting minimum thresholds for users to include in spreadsheet
MESSAGES = 1000 # note that 5000 is GitHub API rate limit
MIN_POSTS = 50
MIN_REACTIONS = 10
MIN_MENTIONS = 10
MIN_SNIPPETS = 10

'''
Scraping messages will yield:
- the members who post frequently 'author' -> 'username'
- we can count how many people @ or reply to someone by scraping 'mentions' -> 'username'
- reactions via 'reactions' -> 'emoji' -> 'name' and 'count'
- for people posting code snippets we look at 'content' and look for posts containing: ```js
- check 'content' for GitHub links
'''
post_authors = {}
author_mentions = {}
author_reactions = {}
author_code_snippets = {}
author_github_links = {}
github_usernames = []

# creating dataframe to store data
discord_data = pd.DataFrame(columns=["Discord Username", "GitHub Username", "Name", "Email", "Location", "Website", "Company", "Twitter", "GitHub Contributions", "Discord Posts", "Bio", "Reactions", "Mentions", "Snippets"]) # new dataframe 
discord_data.set_index('Discord Username', inplace=True)

# this scrapes the last messages from a channel in multiples of 50 (got this from https://www.youtube.com/watch?v=xh28F6f-Cds)
# this describes procedure for 'going back in time': https://stackoverflow.com/questions/67793922/data-scraping-on-discord-using-python
def retrieve_messages(channel_id):
    # Discord authorization key
    headers = {'authorization': '{discordKey}'}

    runs = 0
    before = None

    while runs < MESSAGES / 50:
        query_parameters = f'limit={50}'
        if before is not None:
            query_parameters += f'&before={before}'

        # requesting a batch of messages from the channel
        r = requests.get(f'https://discord.com/api/channels/{channel_id}/messages?{query_parameters}',headers=headers)
        jsonn = json.loads(r.text)

        if len(jsonn) == 0:
            break

        # updating values for all metrics we're tracking
        for value in jsonn:
            author = value['author']['username']
            post_authors[author] = post_authors.get(author, 0) + 1

            for mention in value['mentions']:
                author_mentions[mention['username']] = author_mentions.get(mention['username'], 0) + 1

            num_reaction = 0
            if 'reactions' in value:
                for reaction in value['reactions']:
                    num_reaction += reaction['count']
                author_reactions[author] = author_reactions.get(author, 0) + num_reaction

            if '```js' in value['content']:
                author_code_snippets[author] = author_code_snippets.get(author, 0) + 1
                
            if 'github.com' in value['content']:
                # if no GitHub links for author, create a list
                if author not in author_github_links:
                    author_github_links[author] = []
                author_github_links[author].append(re.findall(r'(https?://g?i?s?t?.?github.com[^\s]+)', value['content']))

                # isolating usernames from links
                if len(author_github_links[author][0]) != 0:
                    link = author_github_links[author][0][0]
                    components = link.split('/')
                    index = 0
                    if 'github.com' in components:
                        index = components.index('github.com') + 1
                    if 'gist.github.com' in components:
                        index = components.index('gist.github.com') + 1
                    if '.' not in components[index]:
                        github_usernames.append(components[index])
                        discord_data.loc[author, ['GitHub Username']] = components[index]
                        #there could me multiple github users in the links sent by one discord user
        runs += 1
        before = json.loads(r.text)[-1]['id']

# reads in channel IDs of channels we will scrape from text file
'''
Servers/channels scraped:
World of Coding: html-css-php, javascript, ui-ux
Javascripters: js-general, projects
DevHelp: ui-design, nodejs, javascript, java, html, css
Dev's House: java, javascript, kotlin, ui-and-ux, web-dev
'''
channels  = open('channels.txt', 'r').readlines()

# adds only users with metrics above minimum thresholds to dataframe
for channel in channels:
    retrieve_messages(channel)
for author in post_authors:
    if post_authors[author] > MIN_POSTS:
        discord_data.loc[author, ['Posts']] = post_authors[author]
for author in author_mentions:
    if author_mentions[author] > MIN_MENTIONS:
        discord_data.loc[author, ['Mentions']] = author_mentions[author]
for author in author_reactions:
    if author_reactions[author] > MIN_REACTIONS:
        discord_data.loc[author, ['Reactions']] = author_reactions[author]
for author in author_code_snippets:
    if author_code_snippets[author] > MIN_SNIPPETS:
        discord_data.loc[author, ['Snippets']] = author_code_snippets[author]

# connection to GitHub API with authorization key
headers = {'Authorization': f'token {githubToken}',
           'Accept': 'application/vnd.github+json'} 

# scrapes all user data from GitHub API
def get_user_info(username):
    url = f'https://api.github.com/users/{username}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Failed to retrieve data: {response.content}')
        return None    

# counts total number of contributions in GitHub
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

# adds GitHub data to dataframe for all users who have GitHub links in their posts
user_info = {}
for username in github_usernames:
    try:
        all_info = get_user_info(username)
        user_info[username] = [all_info['hireable'], all_info['public_repos'], all_info['public_gists'], all_info['followers'], all_info['following'], all_info['created_at']]
        discord_data.loc[username, ['Email', 'Name', 'Company', 'Location', 'Website', 'Bio', 'Twitter']] = [all_info['email'], all_info['name'], all_info['company'], all_info['location'], all_info['blog'], all_info['bio'], all_info['twitter_username']]
        discord_data.loc[username, ['GitHub Contributions']] = get_total_user_contributions(username, headers)
    except:
        print(f'Failed to retrieve data for {username}')
# writes dataframe to csv file
discord_data.to_csv('discord_data.csv')


# def get_user_email(username):
#     url = f'https://api.github.com/users/{username}'
#     response = requests.get(url, headers=headers)
#     if response.status_code == 200:
#         user_data = response.json()
#         return user_data.get('email', 'n/a')  # Return the email if available, otherwise none
#     else:
#         print(f'Failed to retrieve data for {username}: {response.content}')
#         return 'n/a'

# # ADVANCED FUNCTIONS TESTING

# language = 'JavaScript'
# min_followers = 50
# min_stars = 100
# min_contributions = 500
# eastern_european_countries = [
#     "Eastern Europe","Eastern European", "Russia", "Ukraine", "Poland", "Romania",
#     "Czech Republic", "Hungary", "Belarus",
#     "Bulgaria", "Slovakia", "Croatia", "Moldova",
#     "Bosnia and Herzegovina", "Albania", "Lithuania",
#     "North Macedonia", "Slovenia", "Latvia", "Estonia",
#     "Montenegro", "Luxembourg", "Serbia", "Cyprus",
#     "Azerbaijan", "Georgia", "Armenia", "Kosovo"
# ]

'''
Sample output of scraping Discord messages:
{'id': '1169391890202886184', 'type': 0, 'content': "I appreciate your dedication yo help me, but I've found a solution :)\nI just needed to return a copy of 
the new post instead of the post itself.", 'channel_id': '661260205564231704', 
'author': {'id': '724558518870605874', 'username': 'princetoast.', 'avatar': 'e4fce00d1807336babee29386fa51777', 'discriminator': '0', 'public_flags': 128, 'premium_type': 2, 'flags': 128, 'banner': None, 'accent_color': None, 'global_name': '🇵🇸 Prince Toast', 'avatar_decoration_data': None, 'banner_color': None}  
, 'attachments': [], 'embeds': [], 
'mentions': [{'id': '1108326697524277348', 'username': 'r.the_tea', 'avatar': '2ea66bcb45ce72b930d0a2884c4da24b', 'discriminator': '0', 'public_flags': 256, 'premium_type': 0, 'flags': 256, 'banner': None, 'accent_color': None, 'global_name': 'T', 'avatar_decoration_data': None, 'banner_color': None}], 'mention_roles': [], 'pinned': False, 'mention_everyone': False, 'tts': False, 'timestamp': '2023-11-01T21:45:52.875000+00:00', 'edited_timestamp': None, 'flags': 0, 'components': [], 'message_reference': {'channel_id': '661260205564231704', 'message_id': '1169391502439497828', 'guild_id': '661257119588417627'}, 'referenced_message': {'id': '1169391502439497828', 'type': 0, 'content': "Yo I'm taking too long, I test something similar, but in JS, not Typescript\nSo don't rely much on me", 'channel_id': '661260205564231704', 'author': {'id': '1108326697524277348', 'username': 'r.the_tea', 'avatar': '2ea66bcb45ce72b930d0a2884c4da24b', 'discriminator': '0', 'public_flags': 256, 'premium_type': 0, 'flags': 256, 'banner': None, 'accent_color': None, 'global_name': 'T', 'avatar_decoration_data': None, 'banner_color': None}, 'attachments': [], 'embeds': [], 'mentions': [], 'mention_roles': [], 'pinned': False, 'mention_everyone': False, 'tts': False, 'timestamp': '2023-11-01T21:44:20.425000+00:00', 'edited_timestamp': None, 'flags': 0, 'components': []}} 


{'id': '1169392028195504188', 'type': 0, 'content': '>thank <@1108326697524277348>', 'channel_id': '661260205564231704', 'author': {'id': '724558518870605874', 'username': 'princetoast.', 'avatar': 'e4fce00d1807336babee29386fa51777', 'discriminator': '0', 'public_flags': 128, 'premium_type': 2, 'flags': 128, 'banner': None, 'accent_color': None, 'global_name': '🇵🇸 Prince Toast', 'avatar_dec  
oration_data': None, 'banner_color': None}, 'attachments': [], 'embeds': [], 'mentions': [{'id': '1108326697524277348', 'username': 'r.the_tea', 'avatar': '2ea66bcb45ce72b930d0a2884c4da24b', 'discriminator': '0', 'public_flags': 256, 'premium_type': 0, 'flags': 256, 'banner': None, 'accent_color': None, 'global_name': 'T', 'avatar_decoration_data': None, 'banner_color': None}], 'mention_roles': [], 'pinned': False, 'mention_everyone': False, 'tts': False, 'timestamp': '2023-11-01T21:46:25.775000+00:00', 'edited_timestamp': None, 'flags': 0, 'components': [], 
'reactions': [{'emoji': {'id': None, 'name': '💖'}, 'count': 1, 'count_details': {'burst': 0, 'normal': 1}, 'burst_colors': [], 'me_burst': False, 'burst_me': False, 'me': False, 'burst_count': 0}]}
'''
'''
Sample output of scraping GitHub API:
{'florinpop17': {'repos_url': 'https://api.github.com/users/florinpop17/repos', 
'name': 'Florin Pop', 'company': 'iCodeThis.com', 'blog': 'www.florin-pop.com', 'location': 'Romania', 
'email': 'popflorin1705@yahoo.com', 'hireable': True, 'bio': 'Dev & YouTuber\r\n\r\nCreator of https://iCodeThis.com', 'twitter_username': 'florinpop1705', 
'public_repos': 85, 'public_gists': 44, 'followers': 12694, 'following': 34, 'created_at': '2014-02-15T20:09:42Z'}, 
'''