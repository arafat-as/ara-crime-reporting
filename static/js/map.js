/**
 * Leaflet.js Map Integration for CrimeAlert NG
 */

class CrimeMap {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.map = null;
        this.markers = L.layerGroup();
        
        // Default center: Lagos, Nigeria
        this.defaultCenter = [6.5244, 3.3792];
        this.defaultZoom = 11;
        
        this.options = {
            interactive: true,
            ...options
        };
        
        this.initMap();
    }
    
    initMap() {
        const container = document.getElementById(this.containerId);
        if (!container) return;
        
        // Create map instance
        this.map = L.map(this.containerId).setView(this.defaultCenter, this.defaultZoom);
        
        // Dark theme map tiles (CartoDB Dark Matter)
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(this.map);
        
        this.markers.addTo(this.map);
        
        // If interactive, add click listener
        if (this.options.onClick) {
            this.map.on('click', this.options.onClick);
            this.map.getContainer().style.cursor = 'crosshair';
        }
    }
    
    // Create a custom icon based on severity
    createCustomIcon(severity, iconChar) {
        const colors = {
            'low': '#10b981',
            'medium': '#f59e0b',
            'high': '#f97316',
            'critical': '#ef4444'
        };
        
        const color = colors[severity] || '#3b82f6';
        
        const html = `
            <div style="
                background-color: ${color};
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                border: 2px solid white;
                box-shadow: 0 0 10px ${color};
                color: white;
                font-weight: bold;
                font-size: 14px;
            ">
                <i class="fa-solid fa-triangle-exclamation"></i>
            </div>
        `;
        
        return L.divIcon({
            html: html,
            className: 'custom-leaflet-icon',
            iconSize: [30, 30],
            iconAnchor: [15, 15],
            popupAnchor: [0, -15]
        });
    }
    
    loadMarkers(reports) {
        this.markers.clearLayers();
        
        if (!reports || reports.length === 0) return;
        
        const bounds = [];
        
        reports.forEach(report => {
            if (report.latitude && report.longitude) {
                const icon = this.createCustomIcon(report.severity, report.category?.icon);
                
                const marker = L.marker([report.latitude, report.longitude], { icon: icon });
                
                // Popup content
                const popupContent = `
                    <div style="min-width: 200px; color: #333;">
                        <h4 style="margin: 0 0 5px 0; border-bottom: 1px solid #eee; padding-bottom: 5px;">${report.title}</h4>
                        <p style="margin: 0 0 5px 0; font-size: 12px;"><strong>Category:</strong> ${report.category?.name || 'N/A'}</p>
                        <p style="margin: 0 0 10px 0; font-size: 12px;"><strong>Status:</strong> ${report.status}</p>
                        <a href="/report/${report.id}" style="display: block; text-align: center; background: #00d4ff; color: #fff; padding: 5px; border-radius: 4px; text-decoration: none; font-size: 12px;">View Details</a>
                    </div>
                `;
                
                marker.bindPopup(popupContent);
                this.markers.addLayer(marker);
                
                bounds.push([report.latitude, report.longitude]);
            }
        });
        
        // Fit map to show all markers if there are any
        if (bounds.length > 0) {
            this.map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
        }
    }
    
    // For report form: place a single draggable marker
    setDraggableMarker(lat, lng, onDragEnd) {
        this.markers.clearLayers();
        
        const icon = this.createCustomIcon('medium', '📍');
        const marker = L.marker([lat, lng], { 
            icon: icon,
            draggable: true
        });
        
        marker.on('dragend', function(e) {
            const position = marker.getLatLng();
            if (onDragEnd) onDragEnd(position.lat, position.lng);
        });
        
        this.markers.addLayer(marker);
        this.map.setView([lat, lng], 15);
        
        return marker;
    }
}
