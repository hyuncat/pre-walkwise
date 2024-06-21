let map = null; // Holds the leaflet map object

$(document).ready(function() {
    // Initialize the map on document ready
    map = L.map('map').setView([39.926117, 116.315750], 13); // Starting coords (Beijing for now)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 20,
        attribution: '© OpenStreetMap'
    }).addTo(map);
    
    // Initialize a layer group for markers
    var polylineLayer = L.layerGroup().addTo(map);
    var markersLayer = L.layerGroup().addTo(map);

    $('#dataForm').submit(function(event) {
        event.preventDefault();
        
        polylineLayer.clearLayers();
        markersLayer.clearLayers(); 

        // Get the selected person's text and update the secondary title
        var selectedPersonText = $('#person option:selected').text();
        var selectedDate = $('#date option:selected').text();
        $('#personHeading').html(`<h2>Person ${selectedPersonText} on ${selectedDate}</h2>`); // Update the secondary title

        $.post('/geojsondata', $(this).serialize(), function(data) {
            var parsedData = JSON.parse(data);
            var bounds = []; // Array to collect all coordinates
            var original_coords = [];
            var filtered_coords = [];

            // Define the polylines first without adding them
            L.geoJson(parsedData, {
                onEachFeature: function (feature, layer) {
                    if (feature.properties.type === 'original') {
                        original_coords.push([feature.geometry.coordinates[1], feature.geometry.coordinates[0]]);
                    } else {
                        filtered_coords.push([feature.geometry.coordinates[1], feature.geometry.coordinates[0]]);
                    }
                    bounds.push([feature.geometry.coordinates[1], feature.geometry.coordinates[0]]);
                }
            });

            // Add polylines for original and filtered data
            if (original_coords.length > 0) {
                L.polyline(original_coords, {color: '#3480eb', weight: 10}).addTo(polylineLayer);
            }
            if (filtered_coords.length > 0) {
                L.polyline(filtered_coords, {color: '#FF0000', weight: 3}).addTo(polylineLayer);
            }

            // Then define and add points
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
                    var tooltipTitle =feature.properties.type === 'original' ?  'Original' : 'Filtered';
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
                    bounds.push([feature.geometry.coordinates[1], feature.geometry.coordinates[0]]);
                }
            }).addTo(markersLayer);

            // If there are bounds, fit the map to these bounds
            if (bounds.length > 0) {
                map.fitBounds(bounds);
            }
        });
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