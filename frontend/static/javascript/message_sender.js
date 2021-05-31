/* constants */
var MESSAGE_HISTORY_OFFSET, USER_ATTRIBUTES_OFFSET;
var MIN_WINDOW_SIZE = 600;

$(window).load(function() {
    MESSAGE_HISTORY_OFFSET = $("#top-nav-container").outerHeight(true) +
                             $("#message-history-header").outerHeight(true) +
                             $("#message-send").outerHeight(true);
    USER_ATTRIBUTES_OFFSET = $("#top-nav-container").outerHeight(true) +
                             $("#main-attributes").outerHeight(true) +
                             $("#user-attributes .panel-heading").outerHeight(true) +
                             parseInt($("#user-attributes").css("margin-bottom")) +
                             parseInt($("#user-attributes").css("border-top")) +
                             parseInt($("#user-attributes").css("border-bottom"));
});


/* enables/disables send message button */
$("#message-content").on("keyup", function() {
    if (!DISABLED) {
        if ($(this).val().trim()) {
            $("#message-send-button").removeAttr("disabled").removeClass("disabled");
        } else {
            $("#message-send-button").attr("disabled", true).addClass("disabled");
        }
    }
});


/* Adjusts max-height of element to window height - offset */
function setMaxHeight(element, offset, minHeight) {
    var height = $(window).height() - offset;
    if (height < minHeight) {
        height = minHeight;
    }
    $(element).css("max-height", height);
}

/* Things to do on document load */
$(window).load(function() {
    // resize message history
    setMaxHeight("#message-history", MESSAGE_HISTORY_OFFSET, MIN_WINDOW_SIZE - MESSAGE_HISTORY_OFFSET); // 340px for everything not including this div
    // resize user attributes
    setMaxHeight("#user-attributes .panel-body", USER_ATTRIBUTES_OFFSET, MIN_WINDOW_SIZE - USER_ATTRIBUTES_OFFSET); // 358px for everything not including this div
    // automatically scroll to the bottom of the message history
    $('#message-history').scrollTop($('#message-history')[0].scrollHeight);
});

/* Things to do on window resize */
$(window).on('resize', function(){
    // resize message history
    setMaxHeight("#message-history", MESSAGE_HISTORY_OFFSET, MIN_WINDOW_SIZE - MESSAGE_HISTORY_OFFSET); // 340px for everything not including this div
    // resize user attributes
    setMaxHeight("#user-attributes .panel-body", USER_ATTRIBUTES_OFFSET, MIN_WINDOW_SIZE - USER_ATTRIBUTES_OFFSET); // 358px for everything not including this div
});

/* Send message click action */
$("#message-send-button").on("click", function(e) {
    // prevent submit default action
    e.preventDefault();
    var userId = $("#user-id").val();
    var cohortId = $("#cohort-id").val();
    var message = $("#message-content").val();
    if (message.trim() == "") {
        return;
    }
    // warn about sending questions in the middle of surveys
    if ($("#active-session").text() == "Yes") {
        $("#caution-sending-questions").modal("show");
        return;
    } else {
        sendManualMessage(userId, cohortId, message);
    }
});

/* Send custom message */
function sendManualMessage(userId, cohortId, message) {
    if (typeof userId === "undefined") {
        userId = $("#user-id").val();
    }
    if (typeof cohortId === "undefined") {
        cohortId = $("#cohort-id").val();
    }
    if (typeof message === "undefined") {
        message = $("#message-content").val();
    }
    showStatus(function() {
        // clear send box
        $("#message-content").val("");
        // change sending text and disable button
        $("#message-send-button").text("Sending...").addClass("disabled");
        return $.post("/send_manual_message", {
            "user_id": userId,
            "cohort_id": cohortId,
            "message": message
        }).done(function(response) {
            // if reload is specified, reload
            if (response["reload"] == "true") {
                location.reload(true);
            }
            // reload history
            $("#message-history").load(window.location.pathname + " #message-history > *", function() {
                // automatically scroll to the bottom of the message history
                $('#message-history').scrollTop($('#message-history')[0].scrollHeight);
            });
        }).fail(function(response) {
            // pass
        }).always(function() {
            $("#message-send-button").text("Send").removeClass("disabled");
        });
    }, "Sending message", "Message sent", "Error: Failed to send message");
}

/* Goes to the next unhandled message in the viewport */
function goToNextUnhandledMessage() {
    var container = $("#message-history");
    var scrollTo;
    // iterate through all messages needing review to select closet to viewport
    $(".needs-review").each(function() {
        if ($(this).position().top < 0) {
            scrollTo = $(this);
        }
    });
    // if there are still messages, scroll to message
    if (scrollTo) {
        container.animate({
            scrollTop: scrollTo.offset().top - container.offset().top + container.scrollTop() - 24
        }, 500);
    // otherwise, shake to let user know
    } else {
        $("#message-history").animate({
            "padding-top": 36
        }, 200).animate({
            "padding-top": 16
        }, 200);
    }
}

/* Un-mark user and messages as unhandled */
function markAsHandled(userId) {
    $.post(
        "/mark_as_handled",
        {"userId": userId}
    ).done(function() {
        location.reload();
    }).fail(function() {
        alert("Sorry, there was a problem in marking this user as handled.");
    });
}

/* DUPLICATE CODE FROM user_management.js START */

/* launches modal for changing user status (except delete, that's in its own function) */
function launchChangeUserStatus() {
    var currentStatus = $("#status").text();
    var newStatus = currentStatus == "active" ? "paused" : "active";
    var newStatusLabel = newStatus == "active" ? "Activate" : "Pause";
    //if User Status isn't changeable, stops the function
    if (currentStatus != "inactive" && currentStatus != "paused" && currentStatus != "active") {
        return false;
    }
    //if Cohort Status isn't active, prevents confirmation modal
    if (document.getElementById("cohort-status").value != "active") {
        changeUserStatus(newStatus);
        return true;
    }
    // set modal properties
    setModalProperties("change-user-status", {
        "title": newStatusLabel + " User",
        "button": newStatusLabel + " User",
        "buttonAction": "changeUserStatus('" + newStatus + "')"
    });
    // populate modal with values
    $("#change-user-status-new-status-verb").html(newStatusLabel.toLowerCase());
    $("#change-user-status-phone-number").html(
        $("#user-phone").text()
    );
    $("#change-user-status-pause-message, #change-user-status-activate-message").hide();
    if (newStatus == "active") {
        $("#change-user-status-activate-message").show();
    } else if (newStatus == "paused") {
        $("#change-user-status-pause-message").show();
    }
    // show modal
    $("#change-user-status").modal("show");
}    

/* change user status from inactive to active */
function changeUserStatus(newStatus) {
    var userId = document.getElementById("user-id").value;
    // hide change status modal
    $("#change-user-status").modal("hide");
    showStatus(function() {
        // submit data
        return post("/set_user_attribute", {
            "attribute_name": "status",
            "new_value": newStatus,
            "user_id": userId
        }, false)
        // iff successful
        .done(function() {
            // redoes display of User Status
            $("#status").text(newStatus);
            document.getElementById("status").className = newStatus;
        })
        // if fail
        .fail(function() {
            // undo changes
            document.execCommand("undo");
        })
    }, "Saving status", "Status saved", "Error: Status not saved"); 
}

/* save contenteditable changes to database */
function saveContent(element) {
    var attributeName = element.attr("data-custom-attr");
    var newText = element.text().trim();
    var objectId = document.getElementById("user-id").value;
    // prevent editing in same field until it's reloaded
    element.attr("contenteditable", false).removeClass("editable");
    // if the field is a phone number, add +1 to the beginning to match database
    if (attributeName == "phonenum") {
        newText = "+1" + newText;
    }
    // wrap with showStatus to show user status of request
    showStatus(function() {
        var $this = element;
        console.log($this.attr('id'));
        return post("/set_user_attribute", {
            "attribute_name": attributeName,
            "new_value": newText,
            "user_id": objectId
        }, false)
        // if successful
        .done(function() {
            var thisid = "#" + $this.attr('id');
            // loads new values into the element
            $.get(objectId + " " + thisid, function(data) {
                $(thisid).replaceWith($(data).find(thisid));
            });
            // give focus back
            $this.focus();
        })
        // if fail
        .fail(function() {
            // undo changes
            document.execCommand("undo");
        })
        .always(function() {
            // undo prevent editing
            element.attr("contenteditable", true).addClass("editable");
        });
    }, "Saving", "Saved", "Error: Not saved");
}

/* DUPLICATE CODE FROM user_management.js END */