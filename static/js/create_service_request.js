$(document).ready(function() {

	var DEFAULT_POSITION = {
		latitude: 41.8838,
		longitude: -87.632344
	};

	var SMALL_SCREEN_WIDTH = 759;

	var detailsVisible = false;

	var closeServiceChooser = function(selectedServiceName) {
		if (selectedServiceName) {
			$(".selected_service_name").text(selectedServiceName);
		}
		
		var $selectedLabel = $(".selected_service");
		$selectedLabel.css({
			display: "block",
			opacity: "0"
		});
		var height = $selectedLabel[0].offsetHeight;

		$(".service_info").animate({height: height + "px"});
		$selectedLabel.animate({opacity: "1"});
		$(".service_chooser").animate({opacity: "0"});
	};

	var openServiceChooser = function() {
		var $selectedLabel = $(".selected_service");
		var $serviceChooser = $(".service_chooser");

		$serviceChooser.css({display: "block", opacity: "0"});
		var height = $serviceChooser[0].scrollHeight;
		$(".service_info").animate({height: height + "px"});
		$selectedLabel.fadeOut();
		$serviceChooser.animate({opacity: "1"});
	};

	var getAttributeData = function(serviceId) {
		$.ajax({
			url: BASE_URL + "services/" + serviceId + ".json",
			dataType: "json",
			success: function(data, status, xhr) {
				showSrAttributes(data);
			},
			error: function(xhr, status, error) {
				// FIXME: need to actually handle errors
				alert("Something broke!");
			},
			complete: function() {
				if (!detailsVisible) {
					detailsVisible = true;
					$(".sr_details").fadeIn();
					initLocation();
				}
			}
		});
	};

	var showSrAttributes = function(srDefinition) {
		console.log("SR Definition:", srDefinition);

		var attributes = srDefinition.attributes;
		attributes.sort(function(a, b) {
			return a.order - b.order;
		});

		
		var fragment = document.createDocumentFragment();
		for (var i = 0, len = attributes.length; i < len; i++) {
			fragment.appendChild(createAttributeForm(attributes[i]));
		}

		$(".sr_attributes").empty().append(fragment);
	};

	var createAttributeForm = function(attribute) {
		var attributeId = "attribute_" + attribute.code;
		var container = document.createElement("div");
		container.className = "sr_attribute";

		if (attribute.variable) {
			// label
			var label = document.createElement("label");
			label.setAttribute("for", attributeId);
			label.appendChild(document.createTextNode(attribute.description));

			if (attribute.required) {
				var requiredNote = document.createElement("span");
				requiredNote.className = "required_note";
				requiredNote.appendChild(document.createTextNode("(required)"));
				label.appendChild(requiredNote);
			}

			container.appendChild(label);

			// input
			var input = createInputForAttribute(attributeId, attribute);
			container.appendChild(input);
		}
		else {
			container.appendChild(document.createTextNode(attribute.description));
		}

		return container;
	};

	var createInputForAttribute = function(attributeId, attribute) {
		var input;

		if (attribute.datatype === "text") {
			input = document.createElement("textarea");
		}
		else if (attribute.datatype.indexOf("valuelist") > -1) {
			input = document.createElement("select");
			if (attribute.datatype === "multivaluelist") {
				input.multiple = true;
			}

			var values = attribute.values;
			for (var i = 0, len = values.length; i < len; i++) {
				var option = document.createElement("option");
				option.value = values[i].key;
				option.appendChild(document.createTextNode(values[i].name));
				input.appendChild(option);
			}
		}
		else {
			var inputType = {
				number: "number",
				datetime: "datetime"
			}[attribute.datatype] || "text";

			input = document.createElement("input");
			input.type = inputType;

			if (inputType === "datetime" && !("valueAsDate" in input)) {
				input.placeholder = "Needs a picker.";
			}
		}

		if (attribute.required) {
			input.required = true;
		}

		input.id = attributeId;
		return input;
	};


	$(".selected_service").on("click", openServiceChooser);

	$(".service_group .service").on("click", function(event) {
		event.preventDefault();

		var $this = $(this);
		if (!$this.hasClass("selected")) {
			$(".service_group .service").removeClass("selected");
			$this.addClass("selected");

			var serviceId = this.getAttribute("data-service-id");
			getAttributeData(serviceId);

			closeServiceChooser($this.text());
		}
	});

	var map;
	var locationMarker;
	var geocoder = new google.maps.Geocoder();

	var initLocation = function() {
		if (navigator.geolocation) {
			// navigator.geolocation.getCurrentPosition(function(position) {
			// 	initMap(position.coords);
			// }, function(error) {
			// 	initMap();
			// });
			initMap();

			$(".gps_button").show().on("click", function(event) {
				event.preventDefault();

				navigator.geolocation.getCurrentPosition(function(position) {
					setMapLatLng(position.coords);
					var point = new google.maps.LatLng(position.coords.latitude, position.coords.longitude);
					geocoder.geocode({latLng: point}, function(results, status) {
						if (status === google.maps.GeocoderStatus.OK && results.length) {
							$("#sr_location").val(results[0].formatted_address);
						}
					});
				});
			});

			$("#sr_location").on("keypress", function(event) {
				if (event.keyCode === 13) {
					event.preventDefault();

					geocoder.geocode({address: this.value}, function(results, status) {
						if (status === google.maps.GeocoderStatus.OK && results.length) {
							console.log(results);
							var location = results[0].geometry.location;
							setMapLatLng({
								latitude: location.lat(),
								longitude: location.lng()
							});
							// $("#sr_location").val(results[0].formatted_address);
						}
					});
				}
			});
		}
		else {
			initMap();
		}
	};

	var initMap = function(position, zoom) {
		var position = position || DEFAULT_POSITION;
		var center = new google.maps.LatLng(position.latitude, position.longitude);

		var supportsTouch = "createTouch" in document;
		var smallTouchScreen = supportsTouch && document.body.offsetWidth <= SMALL_SCREEN_WIDTH;
		var mapContainer = document.getElementById("sr_map");
		var mapOptions = {
			center: center,
			zoom: 17,
			mapTypeId: google.maps.MapTypeId.ROADMAP,
			streetViewControl: false,
			scrollwheel: false,
			disableDefaultUI: smallTouchScreen
		};
		map = new google.maps.Map(mapContainer, mapOptions);
		setMapLatLng(position);

		// for small touch screens, don't bother with allowing dragging; it just makes scrolling hard
		if (smallTouchScreen) {
			var overlay = document.createElement("div");
			$(overlay).css({
				position: "absolute",
				left: "0",
				top: "0",
				width: "100%",
				height: "100%",
				"z-index": "1000"
				// background: "-webkit-gradient(radial, 50% 50%, 80, 50% 50%, 140, from(rgba(255,255,255,0.2)), to(rgba(255,255,255,1)))",
				// "box-shadow": "inset 0 0 100px #fff"
			});
			mapContainer.style.position = "relative";
			mapContainer.appendChild(overlay);

			// var overlayVisible = true;
			// overlay.addEventListener("click", function(event) {
			// 	event.stopPropagation();
			// 	$(this).fadeOut();
			// 	overlayVisible = false;
			// }, false);
			// document.body.addEventListener("click", function(event) {
			// 	if (!overlayVisible) {
			// 		overlayVisible = true;
			// 		$(overlay).fadeIn();
			// 	}
			// }, false);
		}
	};

	var setMapLatLng = function(position) {
		var point = new google.maps.LatLng(position.latitude, position.longitude);
		map.setCenter(point);
		if (locationMarker) {
			locationMarker.setPosition(point);
		}
		else {
			locationMarker = new google.maps.Marker({
				position: point,
				map: map,
				draggable: true
			});
			google.maps.event.addListener(locationMarker, "dragend", function(event) {
				position = {
					latitude: event.latLng.lat(),
					longitude: event.latLng.lng()
				};
				// setMapLatLng(position);
				var point = new google.maps.LatLng(position.latitude, position.longitude);
				geocoder.geocode({latLng: point}, function(results, status) {
					if (status === google.maps.GeocoderStatus.OK && results.length) {
						$("#sr_location").val(results[0].formatted_address);
					}
				});
			});
		}
	};

	
	
});