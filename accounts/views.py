from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import CustomUser, UserProfile
from .forms import CustomUserCreationForm, UserUpdateForm, ProfileUpdateForm

def is_admin_or_superuser(user):
    """Check if user has admin privileges"""
    return user.is_authenticated and (user.role in ['admin', 'superadmin'] or user.is_superuser)

class UserCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new user - Admin only"""
    model = CustomUser
    form_class = CustomUserCreationForm
    template_name = 'accounts/user_create.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def test_func(self):
        return is_admin_or_superuser(self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'User created successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class UserListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List all users - Admin only"""
    model = CustomUser
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def test_func(self):
        return is_admin_or_superuser(self.request.user)
    
    def get_queryset(self):
        queryset = CustomUser.objects.all().order_by('-date_joined')
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                first_name__icontains=search
            ) | queryset.filter(
                last_name__icontains=search
            ) | queryset.filter(
                email__icontains=search
            ) | queryset.filter(
                username__icontains=search
            )
        
        return queryset

class UserUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update user - Admin only"""
    model = CustomUser
    fields = ['first_name', 'last_name', 'email', 'phone', 'role', 'department', 'is_active']
    template_name = 'accounts/user_update.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def test_func(self):
        return is_admin_or_superuser(self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, f'User {form.instance.get_full_name()} updated successfully!')
        return super().form_valid(form)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Add CSS classes to form fields
        for field_name, field in form.fields.items():
            field.widget.attrs['class'] = 'form-control'
        return form

class UserDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """View user details - Admin only"""
    model = CustomUser
    template_name = 'accounts/user_detail.html'
    context_object_name = 'user_obj'
    
    def test_func(self):
        return is_admin_or_superuser(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get user's lead statistics
        user_obj = self.get_object()
        context['lead_stats'] = {
            'total_leads': user_obj.assigned_leads.count(),
            'won_leads': user_obj.assigned_leads.filter(status='won').count(),
            'active_leads': user_obj.assigned_leads.exclude(status__in=['won', 'lost']).count(),
        }
        return context

@login_required
def profile_view(request):
    """View current user's profile"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    context = {
        'profile': profile,
        'user': request.user
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def profile_update(request):
    """Update current user's profile"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, request.FILES, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile
    }
    return render(request, 'accounts/profile_update.html', context)

@login_required
@user_passes_test(is_admin_or_superuser)
def user_toggle_status(request, pk):
    """Toggle user active status - Admin only"""
    user = get_object_or_404(CustomUser, pk=pk)
    
    if request.method == 'POST':
        user.is_active = not user.is_active
        user.save()
        
        status = "activated" if user.is_active else "deactivated"
        messages.success(request, f'User {user.get_full_name()} has been {status}.')
    
    return redirect('accounts:user_list')

@login_required
@user_passes_test(is_admin_or_superuser) 
def user_delete(request, pk):
    """Delete user - Admin only"""
    user = get_object_or_404(CustomUser, pk=pk)
    
    if request.method == 'POST':
        user_name = user.get_full_name()
        user.delete()
        messages.success(request, f'User {user_name} has been deleted.')
        return redirect('accounts:user_list')
    
    context = {'user_obj': user}
    return render(request, 'accounts/user_confirm_delete.html', context)

def custom_login_view(request):
    """Custom login view"""
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name()}!')
                
                # Redirect to next URL or dashboard
                next_url = request.GET.get('next', 'dashboard:home')
                return redirect(next_url)
            else:
                messages.error(request, 'Your account is inactive. Please contact admin.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')