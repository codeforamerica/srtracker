// TODO: should support more generic validation
$(document).ready(function() {
    var emailPattern = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i;
    var subscriptionForm = $("#subscription_form");
    var emailInput = $("#update_email");
    
    subscriptionForm.on("submit", function(event) {
        value = emailInput.val();
        if (emailPattern.test(value)) {
            subscriptionForm.removeClass("invalid");
        }
        else {
            event.preventDefault();
            event.stopPropagation();
            subscriptionForm.addClass("invalid");
        }
    });
});