from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import  authenticate, login
from .models import Platvid, Video
from .forms import VideoForm, SearchForm
from django.http import Http404, JsonResponse
import urllib
import requests
from django.forms.utils import ErrorList
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin


YouTube_API_Key = 'AIzaSyCXfghmwef9j7sEMt1Km-N6VsuC-CJW0k0'


def index(request):
    recent_platvids = Platvid.objects.all().order_by('-id')[:3]
    popular_platvids = [Platvid.objects.get(pk=1),Platvid.objects.get(pk=2),Platvid.objects.get(pk=3)]
    return render(request, 'platvids/index.html', {'recent_platvids':recent_platvids, 'popular_platvids': popular_platvids})

@login_required
def dashboard(request):
    platvids = Platvid.objects.filter(user=request.user)
    return render(request, 'platvids/dashboard.html', {'platvids':platvids})

@login_required
def add_video(request, pk):
    form = VideoForm()
    search_form = SearchForm()
    platvid = Platvid.objects.get(pk=pk)
    if not platvid.user == request.user:
        raise Http404

    if request.method=='POST':
        form = VideoForm(request.POST)
        if form.is_valid():
            video = Video()
            video.platvid = platvid
            video.url = form.cleaned_data['url']
        
            parsed_url = urllib.parse.urlparse(video.url)
            video_id = urllib.parse.parse_qs(parsed_url.query).get('v')
            if video_id:
                video.youtube_id = video_id[0]
                response = requests.get(f'https://www.googleapis.com/youtube/v3/videos?part=snippet&id={ video_id[0] }&key={ YouTube_API_Key }')
                json = response.json()
                title = json['items'][0]['snippet']['title']
                video.title  = title
                video.save()
                return redirect('detail_collection', pk)
            else:
                errors = form._errors.setdefault('url', ErrorList())
                errors.append('Needs to be a valid YouTube URL')

    return render(request, 'platvids/add_video.html', {'form':form, 'search_form': search_form, 'platvid':platvid})

@login_required
def video_search(request):
    search_form = SearchForm(request.GET)
    if search_form.is_valid():
        encoded_search_term = urllib.parse.quote(search_form.cleaned_data['search_query'])
        response = requests.get(f'https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=6&q={ encoded_search_term }&key={ YouTube_API_Key }')
        return JsonResponse(response.json())
    return JsonResponse({'error': 'Not able to validate submitted form.'})

class SignUp(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('dashboard')
    template_name = 'registration/signup.html'

#auto login after signup
    def form_valid(self, form):
        view = super(SignUp, self).form_valid(form)
        username, password = form.cleaned_data.get('username'), form.cleaned_data.get('password1')
        user = authenticate(username=username, password=password)
        login(self.request, user)
        return view


#function based view would be hedious to create here! i used class based view instead..
class Create_Collection(LoginRequiredMixin, generic.CreateView):
    model = Platvid
    fields = ['title']
    template_name = 'platvids/create_collection.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        form.instance.user = self.request.user
        super(Create_Collection, self).form_valid(form)
        return redirect('dashboard')


class Detail_Collection(generic.DetailView):
    model = Platvid
    template_name = 'platvids/detail_collection.html'


class Update_Collection(LoginRequiredMixin, generic.UpdateView):
    model = Platvid
    template_name = 'platvids/update_collection.html'
    fields = ['title']
    success_url = reverse_lazy('dashboard')

    def get_object(self):
        platvids = super(Update_Collection, self).get_object()
        if not platvids.user == self.request.user:
            raise Http404
        return platvids


class Delete_Collection(LoginRequiredMixin, generic.DeleteView):
    model = Platvid
    template_name = 'platvids/delete_collection.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self):
        platvids = super(Delete_Collection, self).get_object()
        if not platvids.user == self.request.user:
            raise Http404
        return platvids


class DeleteVideo(LoginRequiredMixin, generic.DeleteView):
    model = Video
    template_name = 'platvids/delete_video.html'
    success_url = reverse_lazy('dashboard')

    def get_object(self):
        video = super(DeleteVideo, self).get_object()
        if not video.platvid.user == self.request.user:
            raise Http404
        return video