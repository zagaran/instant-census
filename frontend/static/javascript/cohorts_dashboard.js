function downloadData(cohortId) {
    // check to make sure something is checked
    var count = 0;
    $(".download-data-format").each(function() {
        if ($(this).is(":checked")) {
            count += 1;
        }
    });
    if (count == 0) {
        // TODO: front end error reporting
        alert("Please select what you wish to download.");
    } else {
        showStatus(function() {
            // create custom url
            var url = "/download/custom/" + cohortId + "?"
            var modalId = "download-data-" + cohortId;
            // download cohort users
            if ($("#" + modalId + " #download-cohort-users").is(":checked")) {
                // gather which users to download (default to include them all)
                var status_list = [
                                 "active",
                                 "pending",
                                 "invalid",
                                 "waitlist",
                                 "paused",
                                 "disabled",
                                 "inactive",
                                 "deleted"
                                ]
                for (var i = 0; i < status_list.length; i++) {
                    if (!$("#" + modalId + " #user-status-" + status_list[i]).is(":checked")) {
                        status_list.splice(i, 1);
                        i -= 1; // to account for index after removing the element
                    }
                }
                // if list is not empty, create custom url
                if (status_list.length > 0) {
                    url += "download_cohort_users=true&statuses=";
                    // add each status to url
                    for (var i = 0, len = status_list.length; i < len; i++) {
                        url += status_list[i] + ",";
                    }
                    url += "&";  // to allow for continuation of GET url
                }
            }
            // download message histories
            if ($("#" + modalId + " #download-user-message-histories").is(":checked")) {
                // get which type of message to download
                var type = $("#" +  modalId + " input[name='download-user-message-histories-options']:checked").val();
                url += "download_user_message_histories=true&type=" + type;
                url += "&";  // to allow for continuation of GET url
            }
            // download question answer data
            if ($("#" + modalId + " #download-question-answer-data").is(":checked")) {
                url += "download_question_answer_data=true";
                url += "&";  // to allow for continuation of GET url
            }
            // send user to download url to initiate download
            window.location.href = url;
            // clear checkboxes and hide modal
            $(".download-data-format").each(function() {
                $(this).prop('checked', false);
                toggleOptionsDiv($(this));
            });
            setDefaultsInOptionsDiv();
            $("#download-data-" + cohortId).modal("hide");
            return $.Deferred().resolve("true");
        }, "Creating your file", "Download initiated", "Error: Unable to initiate download");
    }
}

function changeCohortStatus(cohortId) {
    var newCohortStatus = "";
    var newCohortStatusEnglish = ""; // for status messages
    var current = $("#" + cohortId + "-status").attr("data-status");
    // set new cohort status
    if (current == "paused" || current == "pending") {
        newCohortStatus = 'active';
        newCohortStatusEnglish = "activat";
    } else if (current == 'active') {
        newCohortStatus = 'paused';
        newCohortStatusEnglish = "paus";
    } else {
        return 'Invalid Status Change';
    }
    showStatus(function() {
        // hide modal
        $("#" + cohortId + "-activate-cohort-modal").modal("hide");
        $("#" + cohortId + "-pause-cohort-modal").modal("hide");
        // disable button
        $("#" + cohortId + "-status")
            .attr("disabled", "true")
            .attr("href", "")
            .html("Cohort " + newCohortStatusEnglish + "ing");
        // submit data
        data = {
            "cohort_id": cohortId,
            "new_value": newCohortStatus,
        };
        return $.post(
            "/change_cohort_status",
            data
        ).always(function() {
            $("#" + cohortId + "-panel").load("/cohorts #" + cohortId + "-panel > *", function() {
                enableTooltips();
            });
            $("#customer-info").load("/cohorts #customer-info > *");
        });
    }, newCohortStatusEnglish[0].toUpperCase() + newCohortStatusEnglish.substring(1) + "ing cohort",
       "Cohort " + newCohortStatusEnglish + "ed",
       "Error: Unable to " + newCohortStatusEnglish + "e cohort");
}

function launchAddCohort(cohortId) {
    if(cohortId == 'new') {
        $("#cohort-name").val("");
        $("#area-code").val("");
    } else {
        $("#cohort-id").val(cohortId);
        //  the modal title
        $("#addCohort .modal-title").html("Edit Cohort");
        $("#cohort-name").val($("#" + cohortId + "-name").text());
        $("#welcome-message").val($("#" + cohortId + "-welcome-message").text());
        $("#inactive-limit").val($("#" + cohortId + "-inactive").text());
        $("#inactive-time-limit").val($("#" + cohortId + "-timelimit").text());
        if ($("#" + cohortId + "-area").text() != "None specified") { // jinja2 defaults to "None specified" if the value is None
            $("#area-code").val($("#" + cohortId + "-area").text());
        }
    }
    $('#addCohort').modal('toggle');
}

function addCohort() {
    var cohort_name = $("#cohort-name").val();
    var cohort_id = $("#cohort-id").val();
    var customer_id = $("#customerId").val();
    var welcome_message = $("#welcome-message").val();
    var inactive_limit = $("#inactive-limit").val();
    var inactive_time_limit = $("#inactive-time-limit").val()
    // validation
    if (cohort_name.length > 100) {
        alert("Please enter a cohort name that is 100 characters or fewer.")
        return;
    }
    if (cohort_name.length < 1) {
        alert("Please enter a cohort name.")
        return;
    }
    if (inactive_limit == "") {
        alert("Please input a Non-Response Limit.");
        return;
    }
    if (inactive_limit && isNaN(inactive_limit)) {
        alert("Invalid Non-Response Limit. The limit must be a number. Please input a valid non-response limit.")
        return;
    }
    if (inactive_limit && (inactive_limit < 0)) {
        alert("Invalid Non-Response Limit. The limit must be 0 or greater.")
        return;
    }
    if (inactive_time_limit == "") {
        alert("Please input an Inactive Time Limit.");
        return;
    }
    if (inactive_time_limit && isNaN(inactive_time_limit)) {
        alert("Invalid Inactive Time Limit. The limit must be a number. Please input a valid non-response limit.")
        return;
    }
    if (inactive_time_limit && (inactive_time_limit < 0)) {
        alert("Invalid Inactive Time Limit. The limit must be 0 or greater.")
        return;
    }
    var area_code = $("#area-code").val();
    if (area_code && (isNaN(area_code) || area_code.length != 3)) {
        alert("Invalid Area Code. Area codes must be comprised of 3 digits. Please input a valid area code.")
        return;
    }
    // get data to submit
    var data = {
        "area_code": area_code,
        "cohort_name": cohort_name,
        "customer_id": customer_id,
        "inactive_limit": inactive_limit,
        "inactive_time_limit": inactive_time_limit,
        "welcome_message": welcome_message
    };
    if (cohort_id == "new") {
        post("/create_cohort", data, true);
    } else {
        data = $.extend(data, {
            "cohort_id": cohort_id,
        });
        post("/modify_cohort", data, true);
    }
    $("#addCohort").modal("hide");
}

/* Toggles view of options div for download data */
function toggleOptionsDiv(element) {
    // get options div
    var toggleDiv = element.attr("id") + "-options-div";
    var modalId = "download-data-" + element.attr("data-cohort-id");
    // if checked, show options div
    if (element.is(":checked")) {
        $("#" + modalId + " #" + toggleDiv).stop(true,true).slideDown();
    // else hide
    } else {
        $("#" + modalId + " #" + toggleDiv).stop(true,true).slideUp();
    }
}

/* Sets defaults in the options divs for download data */
function setDefaultsInOptionsDiv() {
    // download cohort users select all
    downloadCohortUsersOptionsSelect("all");
    // download user message histories
    $("#download-user-message-histories-all").prop("checked", true);
}

/********************
 * User interactions
 ********************/
// show/hide download cohort users options div
$(".options-toggle").on("click", function() {
    toggleOptionsDiv($(this));
});

// select all/none cohort users options
function downloadCohortUsersOptionsSelect(type) {
    $("#download-cohort-users-options-div input[type='checkbox']").each(function() {
        if (type == "all") {
            $(this).prop("checked", true);
        } else if (type == "none") {
            $(this).prop("checked", false);
        }
    });
}

/* Show completed cohorts */
function showCompletedCohorts() {
    $("#show-completed-cohorts-button").hide();
    $("#completed-cohorts-container").slideDown();
}