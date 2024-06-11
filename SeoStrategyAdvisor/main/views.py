# Import necessary libraries for advanced keyword analysis
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import logout
from django.shortcuts import HttpResponseRedirect
import requests
from bs4 import BeautifulSoup
import spacy
import re
from .models import Analysis, Suggestion,ContactFormSubmission,OptimizedFactor
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet
from nltk.corpus import stopwords
from collections import Counter
import textstat
import time
from .forms import ContactForm

def contact_us(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # If form data is valid, save it to the database
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            ContactFormSubmission.objects.create(name=name, email=email, message=message)
            return redirect('contact_success')  # Redirect to a success page
    else:
        form = ContactForm()
    return render(request, 'contactus.html', {'form': form})

def contact_success(request):
    return render(request, 'contact_success.html')

def blog_post(request):
    return render(request, 'blog_post.html')
    
def about_us(request):
    return render(request, 'about.html')

# Load spaCy English model
nlp = spacy.load("en_core_web_sm")

# Final code to check factors and also for suggestion
# 1. checking mata tag keywoerds  and description
def check_meta_tags(soup):
    meta_description = soup.find('meta', attrs={'name': 'description'})
    meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
    return meta_description, meta_keywords

# 2. Checking images alt texts 
def check_alt_text(soup):
    images = soup.find_all('img')
    alt_texts = [img.get('alt') for img in images]
    return alt_texts

# checking 
def check_links(soup):
    internal_links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith('/')]
    external_links = [a['href'] for a in soup.find_all('a', href=True) if not a['href'].startswith('/')]
    return internal_links, external_links

def check_header_tags(soup):
    h1_tags = soup.find_all('h1')
    h2_tags = soup.find_all('h2')
    return h1_tags, h2_tags

def check_ssl(url):
    return url.startswith('https://')

def home(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            url = request.POST.get('url')
            keywords = request.POST.get('keywords')

            try:
                response = requests.get(url)
                response.raise_for_status()
                load_time = measure_website_speed(url)
                soup = BeautifulSoup(response.content, 'html.parser')
                content = soup.get_text()
                title = soup.find('title').get_text().lower()
                heading = soup.find('h1').get_text().lower()
            except requests.RequestException as e:
                content = f"Error fetching content: {str(e)}"

            nlp = spacy.load("en_core_web_sm")
            doc = nlp(content)
            keyword_list_def = [keyword.strip() for keyword in keywords.split(',')]
            keyword_list = get_synonyms_and_originals(keyword_list_def)
            keyword_analysis = {keyword: sum(1 for token in doc if token.lemma_.lower() == keyword.lower()) for keyword in keyword_list}

            analysis = Analysis.objects.create(
                user=request.user, url=url, keywords=keywords, content=content, keyword_analysis=keyword_analysis
            )

            suggestions = []

            cleaned_text = ' '.join(content.split())
            tokens = word_tokenize(cleaned_text.lower())
            stop_words = set(stopwords.words('english'))
            filtered_tokens = [word for word in tokens if word.isalnum() and word not in stop_words]
            word_freq = Counter(filtered_tokens)
            readability_score = textstat.flesch_reading_ease(cleaned_text)
            word_freq_threshold = 10  
            readability_threshold = 50
            if sum(word_freq.values()) > word_freq_threshold and readability_score > readability_threshold:
                OptimizedFactor.objects.create(analysis=analysis, factor='Content Quality', detail=f"Readability value is {readability_score}")
            else:
                Suggestion.objects.create(analysis=analysis, suggestion_text="The quality of content is not Good. Consider enhancing It")

            if load_time <= 2:
                OptimizedFactor.objects.create(analysis=analysis, factor='Load Time', detail="Webpage load time is Optimized!")
            elif load_time <= 3:
                Suggestion.objects.create(analysis=analysis, suggestion_text="Webpage load time Acceptable, but could be improved")
            else:
                Suggestion.objects.create(analysis=analysis, suggestion_text="Webpage load time Needs optimization")

            try:
                headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2 like Mac OS X) AppleWebKit/605.1.1 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1'}
                response = requests.get(url, headers=headers)
                robots_url = f"{url}/robots.txt"
                response_crawl = requests.get(robots_url)
                if '<meta name="viewport" content="width=device-width,initial-scale=1">' in response.text.lower():
                    OptimizedFactor.objects.create(analysis=analysis, factor='Mobile Friendliness', detail="Mobile-friendly")
                else:
                    if any(media_query in response.text for media_query in ["@media only screen and (max-width: 768px)", "@media only screen and (max-width: 992px)"]):
                        OptimizedFactor.objects.create(analysis=analysis, factor='Mobile Friendliness', detail="Mobile-friendly")
                    else:
                        Suggestion.objects.create(analysis=analysis, suggestion_text="Mobile-friendliness uncertain. Needs optimization")
                if response_crawl.status_code == 200:
                    OptimizedFactor.objects.create(analysis=analysis, factor='Crawlability', detail="Web page is Crawlable!")
                else:
                    Suggestion.objects.create(analysis=analysis, suggestion_text="Web page is not Crawlable. Needs Optimization")
            except requests.RequestException:
                None

            for keyword in keyword_analysis:
                if re.search(keyword.lower(), url):
                    OptimizedFactor.objects.create(analysis=analysis, factor='Keyword in URL', detail=f"{keyword} Present in URL")
                else:
                    Suggestion.objects.create(analysis=analysis, suggestion_text=f"Consider adding {keyword} in URL")
                if re.search(keyword.lower(), title):
                    OptimizedFactor.objects.create(analysis=analysis, factor='Keyword in Title', detail=f"{keyword} Present in Title")
                else:
                    Suggestion.objects.create(analysis=analysis, suggestion_text=f"Consider adding {keyword} in Title")
                if re.search(keyword.lower(), heading):
                    OptimizedFactor.objects.create(analysis=analysis, factor='Keyword in Heading', detail=f"{keyword} Present in Heading")
                else:
                    Suggestion.objects.create(analysis=analysis, suggestion_text=f"Consider adding {keyword} in Heading")

            for keyword, count in keyword_analysis.items():
                if keyword.lower() in ['important', 'relevant', 'crucial'] or count > 10:
                    OptimizedFactor.objects.create(analysis=analysis, factor='Keyword Optimization', detail=f"Content well-optimized for '{keyword}'")
                else:
                    Suggestion.objects.create(analysis=analysis, suggestion_text=f"Consider adding '{keyword}' to highlight important information.")

            if keyword_analysis.get('improve') and keyword_analysis['improve'] > 0:
                Suggestion.objects.create(analysis=analysis, suggestion_text="Consider improving the content for better user engagement.")
            
            url = "https://similarwords.p.rapidapi.com/moar"
            headers = {
                "X-RapidAPI-Key": "e74d336c79msh17c25451a7a1684p11d0a5jsnbca04ac372d8",
                "X-RapidAPI-Host": "similarwords.p.rapidapi.com"
            }
            for keyword in keyword_list_def:
                querystring = {"query": keyword}
                response = requests.get(url, headers=headers, params=querystring)
                suggestions.append(f"Similar Words for {keyword} are "+str(response.json()['result']))

            meta_description, meta_keywords = check_meta_tags(soup)
            if meta_description:
                OptimizedFactor.objects.create(analysis=analysis, factor='Meta Description', detail="Meta description present")
            else:
                Suggestion.objects.create(analysis=analysis, suggestion_text="Consider adding a meta description")
            if meta_keywords:
                OptimizedFactor.objects.create(analysis=analysis, factor='Meta Keywords', detail="Meta keywords present")
            else:
                Suggestion.objects.create(analysis=analysis, suggestion_text="Consider adding meta keywords")

            alt_texts = check_alt_text(soup)
            if all(alt_texts):
                OptimizedFactor.objects.create(analysis=analysis, factor='Alt Text', detail="All images have alt text")
            else:
                Suggestion.objects.create(analysis=analysis, suggestion_text="Some images are missing alt text")

            internal_links, external_links = check_links(soup)
            if internal_links:
                OptimizedFactor.objects.create(analysis=analysis, factor='Internal Links', detail=f"{len(internal_links)} internal links present")
            else:
                Suggestion.objects.create(analysis=analysis, suggestion_text="No internal links found")
            if external_links:
                OptimizedFactor.objects.create(analysis=analysis, factor='External Links', detail=f"{len(external_links)} external links present")
            else:
                Suggestion.objects.create(analysis=analysis, suggestion_text="No external links found")

            h1_tags, h2_tags = check_header_tags(soup)
            if h1_tags:
                OptimizedFactor.objects.create(analysis=analysis, factor='H1 Tags', detail=f"{len(h1_tags)} H1 tags present")
            else:
                Suggestion.objects.create(analysis=analysis, suggestion_text="No H1 tags found")
            if h2_tags:
                OptimizedFactor.objects.create(analysis=analysis, factor='H2 Tags', detail=f"{len(h2_tags)} H2 tags present")
            else:
                Suggestion.objects.create(analysis=analysis, suggestion_text="No H2 tags found")

            if check_ssl(url):
                OptimizedFactor.objects.create(analysis=analysis, factor='SSL Certificate', detail="Website is using HTTPS")
            else:
                Suggestion.objects.create(analysis=analysis, suggestion_text="Website is not using HTTPS")

            if suggestions:
                for suggestion_text in suggestions:
                    Suggestion.objects.create(analysis=analysis, suggestion_text=suggestion_text)

            analyses = Analysis.objects.filter(user=request.user)
            suggestions = Suggestion.objects.filter(analysis=analysis)

            return render(request, 'analysis_result.html', {'analysis': analysis, 'suggestions': suggestions, 'analyses': analyses})
        else:
            return redirect('/signin')

    return render(request, 'home.html')

def profile(request):
    user = request.user
    analyses = Analysis.objects.filter(user=user)

    if request.method == 'POST':
        if user.is_authenticated:
            url = request.POST.get('url')
            keywords = request.POST.get('keywords')

            # Scrape the content from the provided URL
            try:
                response = requests.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                content = soup.get_text()
            except requests.RequestException as e:
                content = f"Error fetching content: {str(e)}"

            # Perform advanced keyword analysis using spaCy
            doc = nlp(content)
            keyword_list = [keyword.strip() for keyword in keywords.split(',')]
            keyword_analysis = {keyword: sum(1 for token in doc if token.lemma_.lower() == keyword.lower()) for keyword in keyword_list}

            # Save the user's analysis request to the database
            analysis = Analysis.objects.create(
                user=user, url=url, keywords=keywords, content=content, keyword_analysis=keyword_analysis
            )

            # Add suggestions based on the analysis (customize this logic based on your requirements)
            suggestions = []
            for keyword, count in keyword_analysis.items():
                if keyword.lower() in ['important', 'relevant', 'crucial'] or count > 10:
                    suggestions.append(f"Your content is well-optimized for '{keyword}' Keep up the good work!")
                else:
                    suggestions.append(f"Consider adding '{keyword}' to highlight important information.")




            if suggestions:
                for suggestion_text in suggestions:
                    Suggestion.objects.create(analysis=analysis, suggestion_text=suggestion_text)

            # Retrieve the user's analyses
            analyses = Analysis.objects.filter(user=user)
            suggestions = Suggestion.objects.filter(analysis=analysis)


            # Pass the analysis, suggestions, and analyses to the template
            return render(request, 'analysis_result.html', {'analysis': analysis, 'suggestions': suggestions, 'analyses': analyses})
        else:
            return redirect('/signin')

    return render(request, 'profile.html', {'user': user, 'analyses': analyses})

def signup(request):
    if request.user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect('/')
        else:
            return render(request, 'signup.html', {'form': form})
    else:
        form = UserCreationForm()
        return render(request, 'signup.html', {'form': form})

def signin(request):
    if request.user.is_authenticated:
        # return render(request, 'home.html')
        return redirect('/')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/profile') #profile
        else:
            msg = 'Error Login'
            form = AuthenticationForm(request.POST)
            return render(request, 'login.html', {'form': form, 'msg': msg})
    else:
        form = AuthenticationForm()
        return render(request, 'login.html', {'form': form})

def signout(request):
    logout(request)
    return redirect('/')


def analysis_result(request, analysis_id):
    analysis = get_object_or_404(Analysis, id=analysis_id)
    suggestions = Suggestion.objects.filter(analysis=analysis)
    return render(request, 'analysis_result.html', {'analysis': analysis, 'suggestions': suggestions})




def measure_website_speed(url, num_measurements=5):
    total_time = 0
    for _ in range(num_measurements):
        start_time = time.time()
        try:
            response = requests.get(url, timeout=5)  # Set a timeout
            end_time = time.time()
            total_time += end_time - start_time
        except requests.exceptions.RequestException as e:
            print(f"Error checking website speed: {e}")
            return None  # Or handle the error as needed
    return total_time / num_measurements


def get_synonyms_and_originals(keyword_list_def):
    synonyms_list = []
    for word in keyword_list_def:
        synonyms = set()
        for syn in wordnet.synsets(word):
            for lemma in syn.lemmas():
                synonyms.add(lemma.name())
        synonyms_list.extend([word] + list(synonyms))  # Add original word + synonyms
    return set(synonyms_list)