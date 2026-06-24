/**
 * Authentication Logic
 */

const Auth = {
    init() {
        this.bindForms();
        // If we have a token but no user object, fetch profile
        if (App.state.token && !App.state.user) {
            this.fetchProfile();
        }
    },
    
    bindForms() {
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');
        
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }
        
        if (registerForm) {
            registerForm.addEventListener('submit', (e) => this.handleRegister(e));
        }
    },
    
    async handleLogin(e) {
        e.preventDefault();
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        const errorDiv = document.getElementById('login-error');
        
        const username = form.username.value;
        const password = form.password.value;
        
        if (errorDiv) errorDiv.style.display = 'none';
        
        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Logging in...';
            
            const response = await App.api('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ username, password })
            });
            
            this.setSession(response.token, response.user);
            App.showToast('Login Successful', `Welcome back, ${response.user.username}`, 'success');
            
            // Redirect based on role
            this.redirectByRole(response.user.role);
            
        } catch (error) {
            if (errorDiv) {
                errorDiv.textContent = error.message;
                errorDiv.style.display = 'block';
            } else {
                App.showToast('Login Failed', error.message, 'error');
            }
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Login';
        }
    },
    
    async handleRegister(e) {
        e.preventDefault();
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        const errorDiv = document.getElementById('register-error');
        
        // Form data
        const data = {
            username: form.username.value,
            email: form.email.value,
            full_name: form.full_name.value,
            phone: form.phone.value,
            password: form.password.value
        };
        
        const confirmPassword = form.confirm_password.value;
        
        if (errorDiv) errorDiv.style.display = 'none';
        
        if (data.password !== confirmPassword) {
            if (errorDiv) {
                errorDiv.textContent = 'Passwords do not match';
                errorDiv.style.display = 'block';
            }
            return;
        }
        
        try {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creating Account...';
            
            const response = await App.api('/auth/register', {
                method: 'POST',
                body: JSON.stringify(data)
            });
            
            this.setSession(response.token, response.user);
            App.showToast('Registration Successful', 'Your account has been created.', 'success');
            
            // Redirect to dashboard
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1000);
            
        } catch (error) {
            if (errorDiv) {
                errorDiv.textContent = error.message;
                errorDiv.style.display = 'block';
            } else {
                App.showToast('Registration Failed', error.message, 'error');
            }
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = 'Create Account';
        }
    },
    
    async fetchProfile() {
        try {
            const data = await App.api('/auth/profile');
            this.setSession(App.state.token, data.user);
        } catch (error) {
            console.error('Failed to fetch profile', error);
            this.logout(false);
        }
    },
    
    setSession(token, user) {
        App.state.token = token;
        App.state.user = user;
        
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(user));
        
        App.renderNavigation();
    },
    
    logout(redirect = true) {
        App.state.token = null;
        App.state.user = null;
        
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        
        if (redirect) {
            window.location.href = '/login';
        }
    },
    
    redirectByRole(role) {
        setTimeout(() => {
            if (role === 'admin') {
                window.location.href = '/admin';
            } else if (role === 'officer') {
                window.location.href = '/officer';
            } else {
                window.location.href = '/dashboard';
            }
        }, 1000);
    },
    
    // Protection for pages
    requireAuth() {
        if (!App.state.token) {
            window.location.href = '/login';
            return false;
        }
        return true;
    },
    
    requireRole(roles) {
        if (!this.requireAuth()) return false;
        
        if (!roles.includes(App.state.user.role)) {
            App.showToast('Access Denied', 'You do not have permission to view this page', 'error');
            setTimeout(() => {
                window.location.href = '/';
            }, 1500);
            return false;
        }
        return true;
    }
};
