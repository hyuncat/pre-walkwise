let map = null; // Holds the leaflet map object
let originalLayer = L.layerGroup();
let kalmanLayer = L.layerGroup();

function toggleLayer(layer, isVisible) {
    if (isVisible) {
        if (!map.hasLayer(layer)) {
            map.addLayer(layer);
        }
    } else {
        if (map.hasLayer(layer)) {
            map.removeLayer(layer);
        }
    }
}

function addPolyline(coordinates, coordType, layer) {
    // Format coordinates as (lat, long) for Leaflet
    let leafletCoords = coordinates.map(coord => [coord[1], coord[0]]);
    // Add polyline segments
    let lineColor = coordType === 'original' ? '#3480eb' : '#FF0000';
    let lineWeight = coordType === 'original' ? 10 : 3;
    L.polyline([leafletCoords], {color: lineColor, weight: lineWeight}).addTo(layer);
}

function addCircleMarkers(parsedData, layer) {
    L.geoJson(parsedData, {
        pointToLayer: function(feature, latlng) {
            var color = feature.properties.type === 'original' ? '#3480eb' : '#FF0000';
            return L.circleMarker(latlng, {
                radius: 8,
                fillColor: color,
                color: "#000",
                weight: 1,
                opacity: 1,
                fillOpacity: 0.4
            });
        },
        onEachFeature: function (feature, layer) {
            // Attach a tooltip to each feature
            var tooltipTitle = feature.properties.type === 'original' ? 'Original' : 'Filtered';
            layer.bindTooltip(`<strong>${tooltipTitle}</strong><br>Coordinates: ${feature.geometry.coordinates[1]}, ${feature.geometry.coordinates[0]}<br>Time: ${feature.properties.time}`, {
                permanent: false,  // true if you want it always displayed
                direction: 'auto'  // it will position the tooltip where there is space
            });
            layer.on('mouseover', function () {
                this.setStyle({
                    fillOpacity: .8
                });
            });
            layer.on('mouseout', function () {
                this.setStyle({
                    fillOpacity: 0.4
                });
            });
            layer.bindPopup(`Coordinates: ${feature.geometry.coordinates[1]}, ${feature.geometry.coordinates[0]}\nTime: ${feature.properties.time}`);
        }
    }).addTo(layer);
}


$(document).ready(function() {
    // Initialize the map on document ready
    map = L.map('map').setView([39.926117, 116.315750], 13); // Starting coords (Beijing for now)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 20,
        attribution: '© OpenStreetMap'
    }).addTo(map);
    
    // Add layer groups for original and Kalman filtered data
    originalLayer.addTo(map);
    kalmanLayer.addTo(map);    

    $('#dataForm').submit(function(event) {
        event.preventDefault();
        
        originalLayer.clearLayers();
        kalmanLayer.clearLayers(); 

        // Update heading based on the current selected person + date
        var selectedPersonText = $('#person option:selected').text();
        var selectedDate = $('#date option:selected').text();
        $('#personHeading').html(`<h2>Person ${selectedPersonText} on ${selectedDate}</h2>`); 

        $.post('/geojsondata', $(this).serialize(), function(gdfJson) {
            var parsedGPSData = JSON.parse(gdfJson);
            var allCoords = []; // Array to collect all coordinates

            // Extract coordinates and categorize by type
            var originalCoords = parsedGPSData.features.filter(f => f.properties.type === 'original');
            var kalmanCoords = parsedGPSData.features.filter(f => f.properties.type === 'filtered');
            
            // Add polylines
            addPolyline(originalCoords.map(f => f.geometry.coordinates), 'original', originalLayer);
            addPolyline(kalmanCoords.map(f => f.geometry.coordinates), 'filtered', kalmanLayer);

            // Add circle markers for each type
            addCircleMarkers({type: 'FeatureCollection', features: originalCoords}, originalLayer);
            addCircleMarkers({type: 'FeatureCollection', features: kalmanCoords}, kalmanLayer);
            
            // Collect all coordinates for bounding
            parsedGPSData.features.forEach(feature => {
                allCoords.push([feature.geometry.coordinates[1], feature.geometry.coordinates[0]]);
            });

            // Fit the map to initially display all the coordinates
            if (allCoords.length > 0) {
                map.fitBounds(allCoords);
            }
        });
    });

    // Toggle layers based on checkbox state
    $('#showOriginal, #showKalman').change(function() {
        toggleLayer(originalLayer, $('#showOriginal').is(':checked'));
        toggleLayer(kalmanLayer, $('#showKalman').is(':checked'));
    });

    // Load initial person and date information
    $('#person').change(function() {
        var personId = $(this).val();
        $.ajax({
            url: '/dates/' + personId,
            type: 'GET',
            success: function(response) {
                var dateSelect = $('#date');
                dateSelect.empty();
                response.forEach(function(date) {
                    dateSelect.append($('<option>', {value: date, text: date}));
                });
            }
        });
    }).trigger('change'); // Trigger change to load dates initially
});