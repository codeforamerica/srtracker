$(document).ready(function() {
    // Hide overlay for flash messages
    var closeOverlay = function(event) {
        var backing = $(event.target).closest(".message_overlay_backing");
        backing.fadeOut(500, function() {
            backing.remove();
        });
    };
    
    $(".message_overlay_backing").on("click", closeOverlay);
    $(".message_overlay .close_button").on("click", function(event) {
        event.preventDefault();
        closeOverlay(event);
    });
    $(".message_overlay").on("click", function(event) {
        event.stopPropagation();
    });
    
    
    // Subscription form validation
    var emailPattern = /^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,4}$/i;
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
