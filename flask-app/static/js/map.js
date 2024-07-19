// Global variables for map creation / layer management
var map = L.map('map').setView([39.926117, 116.315750], 13);
var layerControl;
var currentLayers = [];

L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png', {
    maxZoom: 20,
    attribution: '&copy; <a href="https://carto.com/attributions">CARTO</a> contributors'
}).addTo(map);

var rulerOptions = {
    position: 'bottomleft',
    circleMarker: false,
    lineStyle: {
        color: '#FF0000',
        dashArray: '1,6'
    },
    lengthUnit: {
        display: 'km',
        decimal: 2,
        factor: null
    }
}
var ruler = L.control.ruler(rulerOptions);
ruler.addTo(map);

function polyline(coordinates, coordType) 
{
    // Format coordinates as (lat, long) for Leaflet
    let leafletCoords = coordinates.map(coord => [coord[1], coord[0]]);

    const styleOptions = {
        'original': { color: '#006EC7', weight: 3 },
        'kalman': { color: '#931310', weight: 3 },
        'matched': { color: '#FF87D5', weight: 3 },
        'default': { color: '#000000', weight: 3 }
    };

    // Default style if coordType is not found
    let polylineStyle = styleOptions[coordType] || styleOptions['default'];

    // Create a polyline and add it to a new layer group
    let polylineLayer = L.layerGroup([L.polyline(leafletCoords, polylineStyle)]);

    return polylineLayer;
}

function circles(parsedData, coordType) 
{
    var circleLayer = L.layerGroup(); 

    const colorOptions = { 
        'original': '#1395FF',
        'kalman': '#C61613',
        'matched': '#EB96CE',
        'default': '#000000'
    }

    var geoJsonLayer = L.geoJson(parsedData, {
        pointToLayer: function(feature, latlng) {
            var color = colorOptions[coordType] || colorOptions['default'];

            // Create a darker version of the circle color for outline
            var hslColor = tinycolor(color).toHsl();
            hslColor.l = Math.max(0, hslColor.l - 0.2); // Decrease lightness by 20%
            var darkerColor = tinycolor(hslColor).toHexString();

            return L.circleMarker(latlng, {
                radius: 4.5,
                fillColor: color,
                color: darkerColor,
                weight: 1,
                opacity: 1,
                fillOpacity: 0.4
            });
        },
        filter: function(feature) {
            // Filter out features with null coordinates
            return feature.geometry.coordinates && feature.geometry.coordinates[0] !== null && feature.geometry.coordinates[1] !== null;
        },
        onEachFeature: function (feature, layer) {
            // Attach a tooltip to each feature
            // Uppercase the first letter of the type
            var tooltipTitle = feature.properties.type.charAt(0).toUpperCase() + feature.properties.type.slice(1);
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
            layer.bindPopup(`<strong>${tooltipTitle}</strong><br>Coordinates: ${feature.geometry.coordinates[1]}, ${feature.geometry.coordinates[0]}\nTime: ${feature.properties.time}`);
        }
    });

    circleLayer.addLayer(geoJsonLayer); // Add the GeoJSON layer to the layer group
    return circleLayer; // Return the layer group containing the circles
}

function initMap(person, date) {
    $.post('/init_map', { person: person, date: date }, function(gdfJson) {
        updateMapWithGeoJson(JSON.parse(gdfJson));
    }).fail(function(error) {
        console.error("Error loading initial map data:", error);
    });
}

function updateMapWithGeoJson(parsedGPSData) {
    if (!parsedGPSData || !Array.isArray(parsedGPSData.features)) {
        console.error('Invalid GPS data or features array');
        return;
    }

    var allCoords = [];
    var overlays = {};
    var coordTypes = [...new Set(parsedGPSData.features.map(f => f.properties.type))];

    clearLayers(); // Clears existing layers and control

    coordTypes.forEach(coordType => {
        var features = parsedGPSData.features.filter(f => f.properties.type === coordType);

        // Filter potential null geometry and coordinates
        var filteredFeatures = features.filter(f => 
            f.geometry && 
            f.geometry.coordinates && 
            Array.isArray(f.geometry.coordinates) && 
            f.geometry.coordinates.length === 2 && 
            f.geometry.coordinates[0] !== null && 
            f.geometry.coordinates[1] !== null
        );
        var polylineLayer = polyline(filteredFeatures.map(f => f.geometry.coordinates), coordType);
        var circleLayer = circles({ type: 'FeatureCollection', features: filteredFeatures }, coordType);

        currentLayers.push(polylineLayer);
        currentLayers.push(circleLayer);

        overlays[`Polyline: ${coordType}`] = polylineLayer;
        overlays[`Points: ${coordType}`] = circleLayer;

        filteredFeatures.forEach(feature => {
            allCoords.push([feature.geometry.coordinates[1], feature.geometry.coordinates[0]]);
        });
    });

    addLayersToMap(overlays, allCoords);
}

function clearLayers() {
    currentLayers.forEach(layer => map.removeLayer(layer));
    currentLayers = [];
    if (layerControl) {
        layerControl.remove();
        layerControl = null;
    }
    ruler.addTo(map);
}

function addLayersToMap(overlays, allCoords) {
    currentLayers.forEach(layer => map.addLayer(layer));

    layerControl = L.control.layers(null, overlays, { collapsed: true });
    layerControl.addTo(map);

    if (allCoords.length > 0) {
        map.fitBounds(allCoords);
    }
}

$(document).ready(function() {
    
    // Handle form submissions
    $('#personSelectForm').submit(function(event) {
        event.preventDefault();
        var person = $('#person').val();
        var date = $('#date').val();
        initMap(person, date);
    });

    $('#preprocessForm').submit(async function(event) {
        event.preventDefault();
        var formData = {
            person: $('#person').val(),
            date: $('#date').val(),
            kalmanFilter: $('#kalmanFilter').is(':checked'),
            n_iter: $('#n_iter').val(),
            timeSegment: $('#timeSegment').val(),
            mapMatch: $('#mapMatch').is(':checked'),
            searchRadius: $('#searchRadius').val(),
            gpsAccuracy: $('#gpsAccuracy').val(),
            breakageDistance: $('#breakageDistance').val(),
            interpolationDistance: $('#interpolationDistance').val()
        };
        console.log('Form data:', formData);
    
        try {
            var response = await $.ajax({
                url: '/preprocess',
                type: 'POST',
                data: formData,
                dataType: 'json', // Expecting JSON response
                contentType: 'application/x-www-form-urlencoded; charset=UTF-8'
            });
            console.log(response);
            if (typeof response === 'string') {
                response = JSON.parse(response); // Parse the string to an object
            }
            updateMapWithGeoJson(response); // response is already a JavaScript object
        } catch (error) {
            console.error('Error processing the request', error);
        }
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
                    dateSelect.append($('<option>', { value: date, text: date }));
                });
                // Trigger initial map load
                var initialPerson = $('#person').val();
                var initialDate = $('#date').val();
                initMap(initialPerson, initialDate);
            }
        });
    }).trigger('change'); // Trigger change to load dates initially
});