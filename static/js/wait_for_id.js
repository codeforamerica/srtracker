var POLLING_INTERVAL = 15 * 1000; // milliseconds

var checkToken = function() {
	var url = BASE_URL + "tokens/" + SR_TOKEN + ".json";
	$.ajax({
		url: url,
		cache: false,
		success: function(data) {
			if (data.service_request_id) {
				window.location = BASE_URL + "requests/" + data.service_request_id;
			}
			else {
				setTimeout(checkToken, POLLING_INTERVAL);
			}
		},
		error: function() {
			setTimeout(checkToken, POLLING_INTERVAL);
		}
	});
};

var setupTokenNotification = function(token, email) {
	$.ajax({
		url: BASE_URL + "tokens/" + token + ".json",
		data: {email: email},
		type: "POST",
		success: function(data) {
			$("#notification_email_form").remove();
			$("#notification_email_label").remove();
			$("#notification_email_success").show();
		},
		error: function(error) {
			$("#id_notification_email")[0].disabled = false;
			// TODO: show error message
		}
	})
};

$(document).ready(function() {
	var spinner = new Spinner({
		lines: 12,
		length: 7,
		width: 4,
		radius: 10,
		hwaccel: true,
		top: '0',
		left: '0'
	}).spin(document.getElementById("waiting_spinner"));

	if (window.SR_TOKEN) {
		setTimeout(checkToken, POLLING_INTERVAL);

		$("#notification_email_form").on("submit", function(event) {
			event.preventDefault();
			var emailField = $("#id_notification_email");
			var email = emailField.val();
			var emailPattern = /^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,4}$/i;
			if (email && emailPattern.test(email)) {
				$("#id_notification_email")[0].disabled = true;
				setupTokenNotification(SR_TOKEN, email);
			}
			else {
				// TODO: show error info
			}
		});
	}
});