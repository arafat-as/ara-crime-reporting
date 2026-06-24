/**
 * Logic for submitting and managing crime reports
 */

const Reports = {
    // Current location for the form
    selectedLocation: null,
    
    initForm() {
        if (!Auth.requireAuth()) return;
        
        this.loadCategories();
        this.setupMapPicker();
        this.setupFormSubmit();
        
        // Auto-fill user info if possible (anonymity toggle handles disabling)
        const anonToggle = document.getElementById('is_anonymous');
        if (anonToggle) {
            anonToggle.addEventListener('change', (e) => {
                const infoMsg = document.getElementById('anon-info');
                if (e.target.checked) {
                    infoMsg.style.display = 'block';
                } else {
                    infoMsg.style.display = 'none';
                }
            });
        }
    },
    
    async loadCategories() {
        const select = document.getElementById('category_id');
        if (!select) return;
        
        try {
            const data = await App.api('/categories');
            let html = '<option value="">Select a category...</option>';
            data.categories.forEach(cat => {
                html += `<option value="${cat.id}">${cat.name}</option>`;
            });
            select.innerHTML = html;
        } catch (error) {
            console.error('Failed to load categories', error);
        }
    },
    
    setupMapPicker() {
        const mapContainer = document.getElementById('location-map');
        if (!mapContainer) return;
        
        const latInput = document.getElementById('latitude');
        const lngInput = document.getElementById('longitude');
        
        const map = new CrimeMap('location-map', {
            onClick: (e) => {
                const lat = e.latlng.lat;
                const lng = e.latlng.lng;
                this.updateLocationInputs(lat, lng, latInput, lngInput);
                map.setDraggableMarker(lat, lng, (newLat, newLng) => {
                    this.updateLocationInputs(newLat, newLng, latInput, lngInput);
                });
            }
        });
        
        // Try HTML5 Geolocation
        const geoBtn = document.getElementById('btn-geolocate');
        if (geoBtn) {
            geoBtn.addEventListener('click', () => {
                geoBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Locating...';
                
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                        (position) => {
                            const lat = position.coords.latitude;
                            const lng = position.coords.longitude;
                            this.updateLocationInputs(lat, lng, latInput, lngInput);
                            map.setDraggableMarker(lat, lng, (newLat, newLng) => {
                                this.updateLocationInputs(newLat, newLng, latInput, lngInput);
                            });
                            geoBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Use Current Location';
                        },
                        (error) => {
                            App.showToast('Geolocation Failed', 'Could not get your location. Please click on the map.', 'warning');
                            geoBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Use Current Location';
                        }
                    );
                } else {
                    App.showToast('Not Supported', 'Geolocation is not supported by your browser.', 'warning');
                    geoBtn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Use Current Location';
                }
            });
        }
    },
    
    updateLocationInputs(lat, lng, latInput, lngInput) {
        if (latInput) latInput.value = lat.toFixed(6);
        if (lngInput) lngInput.value = lng.toFixed(6);
        this.selectedLocation = { lat, lng };
    },
    
    setupFormSubmit() {
        const form = document.getElementById('report-form');
        if (!form) return;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const lat = document.getElementById('latitude').value;
            const lng = document.getElementById('longitude').value;
            
            if (!lat || !lng) {
                App.showToast('Location Required', 'Please select a location on the map.', 'warning');
                return;
            }
            
            const submitBtn = form.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting...';
            
            // Using FormData for potential file uploads
            const formData = new FormData(form);
            
            // Handle checkbox boolean
            formData.set('is_anonymous', form.is_anonymous.checked);
            
            try {
                const response = await App.api('/reports', {
                    method: 'POST',
                    body: formData // Fetch wrapper removes Content-Type so browser sets boundary
                });
                
                App.showToast('Report Submitted', 'Your report has been successfully submitted to authorities.', 'success');
                
                setTimeout(() => {
                    window.location.href = `/report/${response.report.id}`;
                }, 1500);
                
            } catch (error) {
                App.showToast('Submission Failed', error.message, 'error');
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Submit Report';
            }
        });
        
        // Image preview logic
        const imageInput = document.getElementById('image');
        const imagePreview = document.getElementById('image-preview');
        
        if (imageInput && imagePreview) {
            imageInput.addEventListener('change', function() {
                if (this.files && this.files[0]) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        imagePreview.src = e.target.result;
                        imagePreview.style.display = 'block';
                    }
                    reader.readAsDataURL(this.files[0]);
                } else {
                    imagePreview.style.display = 'none';
                }
            });
        }
    }
};
