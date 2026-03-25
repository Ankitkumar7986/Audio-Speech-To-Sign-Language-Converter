from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login,logout
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk
from django.contrib.staticfiles import finders
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import speech_recognition as sr
import json
import io
import tempfile
import os

def home_view(request):
	return render(request,'home.html')


# def about_view(request):
# 	return render(request,'about.html')


# def contact_view(request):
# 	return render(request,'contact.html')

def _process_sentence(text):
	"""Shared NLP pipeline: tokenize, POS tag, lemmatize, filter, check video availability."""
	text_lower = text.lower()
	words = word_tokenize(text_lower)

	tagged = nltk.pos_tag(words)
	tense = {}
	tense["future"] = len([word for word in tagged if word[1] == "MD"])
	tense["present"] = len([word for word in tagged if word[1] in ["VBP", "VBZ","VBG"]])
	tense["past"] = len([word for word in tagged if word[1] in ["VBD", "VBN"]])
	tense["present_continuous"] = len([word for word in tagged if word[1] in ["VBG"]])

	stop_words = set(["mightn't", 're', 'wasn', 'wouldn', 'be', 'has', 'that', 'does', 'shouldn', 'do', "you've",'off', 'for', "didn't", 'm', 'ain', 'haven', "weren't", 'are', "she's", "wasn't", 'its', "haven't", "wouldn't", 'don', 'weren', 's', "you'd", "don't", 'doesn', "hadn't", 'is', 'was', "that'll", "should've", 'a', 'then', 'the', 'mustn', 'i', 'nor', 'as', "it's", "needn't", 'd', 'am', 'have',  'hasn', 'o', "aren't", "you'll", "couldn't", "you're", "mustn't", 'didn', "doesn't", 'll', 'an', 'hadn', 'whom', 'y', "hasn't", 'itself', 'couldn', 'needn', "shan't", 'isn', 'been', 'such', 'shan', "shouldn't", 'aren', 'being', 'were', 'did', 'ma', 't', 'having', 'mightn', 've', "isn't", "won't"])

	lr = WordNetLemmatizer()
	filtered_text = []
	for w,p in zip(words,tagged):
		if w not in stop_words:
			if p[1]=='VBG' or p[1]=='VBD' or p[1]=='VBZ' or p[1]=='VBN' or p[1]=='NN':
				filtered_text.append(lr.lemmatize(w,pos='v'))
			elif p[1]=='JJ' or p[1]=='JJR' or p[1]=='JJS'or p[1]=='RBR' or p[1]=='RBS':
				filtered_text.append(lr.lemmatize(w,pos='a'))
			else:
				filtered_text.append(lr.lemmatize(w))

	words = filtered_text
	temp=[]
	for w in words:
		if w=='I':
			temp.append('Me')
		else:
			temp.append(w)
	words = temp

	if tense:
		probable_tense = max(tense,key=tense.get)
		if probable_tense == "past" and tense["past"]>=1:
			words = ["Before"] + words
		elif probable_tense == "future" and tense["future"]>=1:
			if "Will" not in words:
				words = ["Will"] + words
		elif probable_tense == "present":
			if tense["present_continuous"]>=1:
				words = ["Now"] + words

	filtered_text = []
	for w in words:
		path = w + ".mp4"
		f = finders.find(path)
		if not f:
			for c in w:
				filtered_text.append(c)
		else:
			filtered_text.append(w)

	return filtered_text

@csrf_exempt
def process_text(request):
	"""AJAX endpoint: takes text, runs NLP, returns word list as JSON."""
	if request.method == 'POST':
		try:
			data = json.loads(request.body)
			text = data.get('text', '')
			if not text.strip():
				return JsonResponse({'words': []})
			words = _process_sentence(text)
			return JsonResponse({'words': words, 'text': text})
		except Exception as e:
			return JsonResponse({'error': str(e)}, status=500)
	return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required(login_url="login")
def animation_view(request):
	if request.method == 'POST':
		text = request.POST.get('sen')
		words = _process_sentence(text)
		return render(request,'animation.html',{'words':words,'text':text})
	else:
		return render(request,'animation.html')




def signup_view(request):
	if request.method == 'POST':
		form = UserCreationForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request,user)
			# log the user in
			return redirect('animation')
	else:
		form = UserCreationForm()
	return render(request,'signup.html',{'form':form})



def login_view(request):
	if request.method == 'POST':
		form = AuthenticationForm(data=request.POST)
		if form.is_valid():
			#log in user
			user = form.get_user()
			login(request,user)
			if 'next' in request.POST:
				return redirect(request.POST.get('next'))
			else:
				return redirect('animation')
	else:
		form = AuthenticationForm()
	return render(request,'login.html',{'form':form})


def logout_view(request):
	logout(request)
	return redirect("home")


@csrf_exempt
def speech_to_text(request):
	if request.method == 'POST':
		try:
			audio_file = request.FILES.get('audio')
			if not audio_file:
				return JsonResponse({'error': 'No audio file provided'}, status=400)

			# Save to a temp file
			with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
				for chunk in audio_file.chunks():
					tmp.write(chunk)
				tmp_path = tmp.name

			try:
				recognizer = sr.Recognizer()
				# Lower the energy threshold to pick up quieter speech
				recognizer.energy_threshold = 300
				recognizer.dynamic_energy_threshold = False

				with sr.AudioFile(tmp_path) as source:
					# Adjust for ambient noise in the first 0.5 seconds
					recognizer.adjust_for_ambient_noise(source, duration=0.5)
					audio_data = recognizer.record(source)

				# Check if audio has enough data
				if len(audio_data.frame_data) < 1000:
					return JsonResponse({'error': 'Recording too short. Please speak for at least 2 seconds.'}, status=400)

				# Try with en-US first (more common), then en-IN as fallback
				text = None
				for lang in ['en-US', 'en-IN']:
					try:
						text = recognizer.recognize_google(audio_data, language=lang)
						if text:
							break
					except sr.UnknownValueError:
						continue

				if text:
					return JsonResponse({'text': text})
				else:
					return JsonResponse({'error': 'Could not understand the audio. Please speak clearly and closer to the microphone, then try again.'}, status=400)

			except sr.RequestError as e:
				return JsonResponse({'error': f'Google API error: {str(e)}'}, status=500)
			finally:
				if os.path.exists(tmp_path):
					os.unlink(tmp_path)
		except Exception as e:
			return JsonResponse({'error': str(e)}, status=500)
	return JsonResponse({'error': 'Invalid request method'}, status=405)

