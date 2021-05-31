/*
 *   - TODO: make resetInputs() more robust
 */


/**************************************
 * Constants
 **************************************/
var COMMON_UNICODE = {
    "\u201c": '"', // left double smart quote 0x201C
    "\u201d": '"', // right double smart quote 0x201D
    "\u2018": "'", // left single smart quote 0x2018
    "\u2019": "'", // right single smart quote 0x2019
    "\u2014": "-", // em dash 0x2014
    "\u2013": "-", // en dash 0x2013
}
var DEFAULT_INPUT_VALUES = {
    "text": "",
    "number": 1,
    "checkbox": false,
    "hour": 12,
    "select": "",
    "hidden": "", // pass
    "file": "", // pass
};


/**************************************
 * $(document).ready();
 **************************************/
$(document).ready(function() {

    /* prepopulate print date/time */
    printPage(false);

    /* scroll to top if there are flash alerts */
    if ($(".alert-flash").length > 0) {
        window.scrollTo(0, 0);
    }
    $("#status-popup").slideUp(500);

    /* enable tooltips */
    enableTooltips();

});


/**************************************
 * Event listeners
 **************************************/
/* actions button dropdown functionality */
$("#actions-dropdown-button").hover(function() {
    $("#actions-dropdown").stop(true, true).fadeIn(200);
}, function() {
    $("#actions-dropdown").stop(true, true).fadeOut(100);
});


/* prevent buttons from staying on the active state */
$(".btn, #actions-dropdown-button a").on("click mouseleave", function() {
    $(this).blur();
});


/* handle contenteditable changes */
$(document).on("keydown blur", "[contenteditable='true']", function(e) {
    var code = e.keyCode || e.which;
    if (code == 27) { // esc
        // undo changes
        document.execCommand("undo");
        // blur away
        $(this).blur();
    } else if (code == 9 || code == 13) { // 9: tab, 13: enter
        // prevent default tab or enter action
        e.preventDefault();
        // blur away
        $(this).blur();
    } else if (code == 0) { // 0: blur
        // if changes were made
        if ($(this).text() != $(this).attr("data-previous")) {
            // NOTE: will call the saveContent() that is loaded with the page (same name for different pages)
            saveContent($(this));
        }
    }
});


/* strips common unicode from pastes
 * Note: this code block works well for Chrome and contenteditables on FF, but not for some reason
 * not input/textarea on FF, so it's commented out for now
$(window).bind("paste", function(e) {
    e.preventDefault();
    var text = e.originalEvent.clipboardData.getData("text/plain");
    for (var unicode in COMMON_UNICODE) {
        if (COMMON_UNICODE.hasOwnProperty(unicode)) {
            text = text.replace(new RegExp(unicode, 'g'), COMMON_UNICODE[unicode]);
        }
    }
    document.execCommand("insertText", false, text);
});



/* allow fixed top nav to scroll horizontally for smaller screens */
$(window).on("scroll resize", function() {
    $("#top-nav, #sub-nav-container").css({
        "left": -$(this).scrollLeft(),
        "width": $(this).width() + $(this).scrollLeft()
    });
});


/**************************************
 * Functions
 **************************************/
/* enable tooltips */
function enableTooltips() {
    $(function () {
        $("[data-toggle='tooltip']").tooltip()
    })
}


/* post data to server with optional reload */
function post(page, data, reload) {
    return $.post(
        page,
        data
    ).done(function(response) {
        if (reload) {
            location.reload(true); // reload(true) resets the cache on reload in order to make <option selected> work in FF
        }
    }).fail(function(jqXhr, textStatus, errorThrown) {
        /* UNCOMMENT FOR DEBUGGING
        alert("jqXhr: " + jqXhr + "; status: " + textStatus + "; error: " + errorThrown);
        console.log("jqXhr");
        console.log(jqXhr);
        console.log("textStatus");
        console.log(textStatus);
        console.log("errorThrown");
        console.log(errorThrown);
        if (reload) {
        */
        // for flash errors
        location.reload(true);
    });
}


/* print page */
function printPage(print) {
    // populate date/time for printing
    var now = new Date();
    $("#current-date-time").html(now.toString());
    if (print) {
        // print page
        window.print();
    }
}


/* reset user input elements */
/* NOTE: this assumes we don't use values on checkboxes (currently, we
         only care about the :checked value of checkboxes), so this will
         need to be fixed if we change that in the future */
function resetInputs(elementId, customDefaultResets) {
    // reset to defaults
    $("#" + elementId + " input, #" + elementId + " select").each(function() {
        // get input type
        var inputType;
        if ($(this).prop("tagName").toLowerCase() == "input") {
            inputType = $(this).attr("type");
        } else if ($(this).prop("tagName").toLowerCase() == "select") {
            inputType = $(this).attr("data-type") || "select";
        }
        // reset value
        if (inputType in DEFAULT_INPUT_VALUES) {
            if (inputType == "checkbox") {
                $(this).prop("checked", DEFAULT_INPUT_VALUES[inputType]).change(); // to trigger any dependencies
            } else if (inputType == "file" || inputType == "hidden") {
                // pass
            } else {
                $(this).val(DEFAULT_INPUT_VALUES[inputType]).change(); // to trigger any dependencies
            }
        };
    });
    // reset forms in elementId
    $("#" + elementId + " form").each(function() {
        $(this)[0].reset();
    });
    // reset custom defaults TODO: make this DRYer
    if (customDefaultResets) {
        var selectorPrefix;
        var classOrId;
        for (var i = 0, len = customDefaultResets.length; i < len; i++) {
            // get selector (id or class) and name
            if (customDefaultResets[i]["id"]) {
                selectorPrefix = "#";
                classOrId = customDefaultResets[i]["id"];
            } else if (customDefaultResets[i]["class"]) {
                selectorPrefix = ".";
                classOrId = customDefaultResets[i]["class"];
            }
            // reset value
            var defaultValue = customDefaultResets[i]["default"];
            var htmlValue = customDefaultResets[i]["html"];
            if ($(selectorPrefix + classOrId).attr("type") == "checkbox" ||
                $(selectorPrefix + classOrId).attr("type") == "radio") {
                $(selectorPrefix + classOrId).prop("checked", defaultValue).change()
            } else {
                $(selectorPrefix + classOrId).val(defaultValue).change(); // to trigger any dependencies
            }
            if (typeof htmlValue !== "undefined") {
                $(selectorPrefix + classOrId).html(htmlValue);
            }
        }
    }
}


/* sets modal properties, like title, button, etc. */
function setModalProperties(modalId, properties) {
    $("#" + modalId + " .modal-title").html(properties["title"]); // will not reset if empty, since .html() doesn't set
    $("#" + modalId + " .modal-footer a").html(properties["button"]); // will not reset if empty, since .html() doesn't set
    if (properties["buttonAction"]) {
        $("#" + modalId + " .modal-footer a").attr("onclick", properties["buttonAction"]);
    }
    if (properties["buttonHref"]) {
        $("#" + modalId + " .modal-footer a").attr("href", properties["buttonHref"]);
    }
}


/* shows all toShow and hides all toHide */
function showAllHideAll(toShow, toHide, whichActionFirst) {
    if (whichActionFirst == "show") {
        if (toShow) {
            $(toShow).each(function() {
                $(this).show();
            });
        }
    }
    if (toHide) {
        $(toHide).each(function() {
            $(this).hide();
        });
    }
    if (whichActionFirst == "hide") {
        if (toShow) {
            $(toShow).each(function() {
                $(this).show();
            });
        }
    }
}


/***
 * Function: showStatus()
 *
 * Displays status during and after execution of passed in function.
 *
 * Parameters:
 *   functionToExecute = (function) that is to be executed being wrapped by
 *                       this function, should return true for success and
 *                       false if error
 *   progressMessage = (string) that will be displayed during execution
 *   successMessage = (string) that will be displayed after execution
 *                             if successful
 *   errorMessage = (string) that will be displayed after execution
 *                           if error
 *
 * Notes:
 *   This function makes use of the jQuery deferred object as a way of
 *   handling asynchronous responses. However, this means that the function
 *   requires that it's returned a deferred object. You can make use of
 *   $.Deferred().resolve([RESPONSE]) to handle non-asynchronous calls.
 *
 *   If anything other than str("true") is returned (string in order to work
 *   natively with python/Flask), showStatus() will override the original
 *   error message with [RESPONSE]. To return a failed call, you should use
 *   $.Deferred().reject() instead.
 *
 * Example:
 *     showStatus(function() {
 *         // if there is no ajax request, must return a deferred object
 *         return $.Deferred().resolve("true");
 *     }, "Loading", "Loading complete", "Error: could not load page");
 */
var showStatus = (function() {
    var timeOut;
    return function(functionToExecute, progressMessage, successMessage, errorMessage) {
        // display progress status
        $(".status-popup-animated").stop(true, true).show();
        $("#status-popup-message").html(progressMessage);
        $("#status-popup").removeClass().addClass("alert-default").stop(true, true).fadeIn(50);
        // execute function
        setTimeout(function() { // allows DOM to update
            var completedMessage;
            var completedMessageClass;
            functionToExecute().done(function(response, status, jqXHR) {
                // TODO: DRY this out, make it more robust, and expect json all the time
                if (typeof response === "string") {
                    if (response == "true" || response == "success") {
                        completedMessage = successMessage;
                        completedMessageClass = "alert-success";
                    } else {
                        // set error message as long as it's not html
                        completedMessage = response && (!jqXHR || (jqXHR && jqXHR.getResponseHeader("content-type").indexOf("text/html") < 0)) ? response : errorMessage;
                        completedMessageClass = "alert-error";
                    }
                } else if (typeof response === "object") {
                    if (response["__status__"] == "true" || response["__status__"] == "success") {
                        completedMessage = successMessage;
                        completedMessageClass = "alert-success";
                    } else {
                        // set error message as long as it's not html
                        completedMessage = errorMessage;
                        completedMessageClass = "alert-error";
                    }
                }
            }).fail(function() {
                // display error
                completedMessage = "Error: something went wrong in our system";
                completedMessageClass = "alert-error";
            }).always(function() {
                // display completion status
                $("#status-popup").fadeOut(200, function() { // first fade out the old status
                    $(".status-popup-animated").hide();
                    $("#status-popup-message").html(completedMessage);
                    $("#status-popup").removeClass().addClass(completedMessageClass).fadeIn(200);
                    // fade out progress status
                    clearTimeout(timeOut); // so that it resets the fadeOut animation timeout
                    timeOut = setTimeout(function() { $("#status-popup").fadeOut(200); }, 3000);
                });
            });
        }, 100);
    }
})();


/* phone number parsing */
function validatePhoneNumber(phoneNumber) {
    var phoneNumber = phoneNumber.match(/^[\d\+]+/)[0];
    if (phoneNumber.length == 12 && phoneNumber.substring(0, 2) == "+1") {
        return phoneNumber;
    } else if (phoneNumber.length == 11 && phoneNumber.substring(0, 1) != "+") {
        return "+" + phoneNumber;
    } else if (phoneNumber.length == 10) {
        return "+1" + phoneNumber;
    }
    return false;
}






