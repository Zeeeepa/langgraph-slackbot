#!/usr/bin/env python3
"""
Script to scrape the top 10 headlines from Hacker News and send them to Slack.
"""
import requests
from bs4 import BeautifulSoup
import json

def scrape_hacker_news():
    """Scrape the top 10 stories from Hacker News."""
    url = "https://news.ycombinator.com/"
    response = requests.get(url)
    
    if response.status_code != 200:
        return f"Error fetching Hacker News: Status code {response.status_code}"
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all story titles and links
    stories = []
    title_elements = soup.select('.titleline > a')
    score_elements = soup.select('.score')
    
    # Get the first 10 stories
    for i, (title_elem, score_elem) in enumerate(zip(title_elements, score_elements)):
        if i >= 10:  # Only get top 10
            break
            
        title = title_elem.text
        url = title_elem.get('href')
        score = score_elem.text if score_elem else "No score"
        
        stories.append({
            "rank": i + 1,
            "title": title,
            "url": url,
            "score": score
        })
    
    return stories

def format_for_slack(stories):
    """Format the stories for Slack message."""
    if isinstance(stories, str):  # Error message
        return stories
        
    message = "*Top 10 Hacker News Stories*\n\n"
    
    for story in stories:
        message += f"*{story['rank']}.* <{story['url']}|{story['title']}> - {story['score']}\n"
    
    return message

if __name__ == "__main__":
    try:
        # Install required packages if not already installed
        import importlib
        
        required_packages = ['requests', 'beautifulsoup4']
        for package in required_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                print(f"Installing {package}...")
                import subprocess
                subprocess.check_call(['pip', 'install', package])
        
        # Scrape HN and format results
        stories = scrape_hacker_news()
        formatted_message = format_for_slack(stories)
        
        # Print the formatted message (will be sent to Slack by the agent)
        print(formatted_message)
        
    except Exception as e:
        print(f"Error: {str(e)}")
