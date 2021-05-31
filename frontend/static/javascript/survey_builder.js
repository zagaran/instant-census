/*
 *   - TODO: factor out error checking
 *   - TODO: launchAddItem() can use a little factoring/DRYing out, especially with view stuff
 *   - TODO: move defaults up
 */


/**************************************
 * Constants
 **************************************/
var DAYS_OF_WEEK = [
                    "Sunday",
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday"
                   ]
var DEFAULT_RESEND_HOUR = 17;
var DEFAULT_RESEND_NUMBER = 1;
var DEFAULT_RESEND_HOURS = 12;
var MAX_SMS_LENGTH = DISABLE_LENGTH_RESTRICTION ? 1600 : 160;

/**************************************
 * $(document).ready();
 **************************************/
$(document).ready(function() {
    $(".status-hide").hide();
    /* disables editing if cohort completed */
    if (COHORT_COMPLETED) {
        // remove contenteditables
        $("#surveys [contenteditable='true'], #surveys [onclick], .point").each(function() {
            $(this)
                .removeAttr("contenteditable")
                .removeAttr("onclick");
        });
        // remove button blocks
        $("#surveys .button-block").each(function() {
            $(this).remove();
        });
        // remove dropdown options
        $("#surveys option").each(function() {
            if (!$(this).prop("selected")) {
                $(this).remove();
            } else {
                $(this).parent()
                    .attr("disabled", true);
            }
        });
        // change cursor for all elements
        $("#surveys *").each(function() {
            // leave schedule-toggle alone
            if (!$(this).hasClass("schedule-toggle")) {
                $(this).css("cursor", "default");
            }
        })
    }
    /* initiates datepicker */
    $("#schedule-date").datepicker({
        autoclose: true,
        format: "yyyy-mm-dd",
        orientation: "top",
        todayHighlight: true
    });
});


/**************************************
 * $(window).load();
 **************************************/
$(window).load(function() {
    /* resize selects */
    resizeSelects(".dropDown");
});


/**************************************
 * Event listeners
 **************************************/
/* Validate conditional "If ANSWER_VALUE_DISPLAY is __" to make sure doesn't include forbidden words */
$("#conditional-value-new").on("blur", function() {
    if ($("#conditional-field-answer").val() == ANSWER_VALUE &&
        $("#conditional-value-new").val() != "") {
        validateMultipleChoices([$(this).val()])
    };
});


/* when "conditional-value-new-select" is changed, updates the input "conditional-value-new" where the submit draws data from */
$("#conditional-value-new-select").on("change", function() {
    $("#conditional-value-new").val($(this).val());
});

/* when "conditional-value-new-attr" is changed, updates the input "conditional-value-new" where the submit draws data from */
$("#conditional-value-new-attr").on("change", function() {
    $("#conditional-value-new").val($(this).val());
})

/* when "conditional-range-new-select" is changed, updates the input "conditional-range-new" where the submit draw data from */
$("#conditional-range-new-select").on("change", function() {
    $("#conditional-range-new").val($(this).val());
});

/* resize selects */
$(".dropDown").on("change", function() {
    resizeSelects($(this));
});


/* show/hide question types */
$("#new-question-type").on("change", function() {
    var newQuestionType = $(this).val();
    if (newQuestionType == "multiple_choice_parser") {
        $("#multiple-choice-settings").show();
        $("#numeric-settings").hide();
        updateMultipleChoiceInputs();
    } else if (newQuestionType == 'number_parser') {
        $("#multiple-choice-settings").hide();
        $("#numeric-settings").show();
    } else {
        $("#multiple-choice-settings").hide();
        $("#numeric-settings").hide();
    }
});


/* preview text button action */
$(".preview-text").on("click", function() {
    var text = $(this).parent(".button-block").siblings(".message-content").html();
    var cohortId = $("#cohort-id").val();
    $("#preview-form input[name='text']").val(text);
    $("#preview-form input[name='cohort_id']").val(cohortId);
    $("#preview-form").submit();
});


/* show or hide/reset resend options */
$("input[name='resend-radio']").on("click change", function() {
    var checked = $("input[name='resend-radio']:checked").val();
    // if checked, show resend options
    if (checked == "time") {
        $("#resend-time").show();
        $("#resend-hours").hide();
        $("#resend-hour").val(DEFAULT_RESEND_HOUR);
        $("#resend-number").val(DEFAULT_RESEND_NUMBER);
        $("#resend-options").stop(true, true).slideDown(300);
    // if unchecked, hide resend options and reset
    } else if (checked == "hours") {
        $("#resend-time").hide();
        $("#resend-hours").show();
        $("#resend-number").val(DEFAULT_RESEND_NUMBER);
        $("#resend-interval").val(DEFAULT_RESEND_HOURS);
        $("#resend-options").stop(true, true).slideDown(300);
    } else {
        $("#resend-options").stop(true, true).slideUp(200);
        $("#resend-number").val(0);
    }
});


/* toggles schedule visibility and icon */
$(".schedule-toggle").click(function() {
    // else, if not hidden (will have chevron-down)
    if ($(this).hasClass("glyphicon-chevron-down")) {
        // change icon to chevron-down
        $(this).removeClass("glyphicon-chevron-down").addClass("glyphicon-chevron-right");
        // close schedule
        $(this).parent().first().children("div").slice(1).slideUp();
    // else, if hidden (this defaults it to opening)
    } else {
        // change icon to chevron-down
        $(this).removeClass("glyphicon-chevron-right").addClass("glyphicon-chevron-down");
        // open schedule
        $(this).parent().first().children("div").slice(1).stop(true, true).slideDown();
    }
});


/* show/hide warning on add schedule if date/time may be in the past */
$("#schedule-date, #send-hour-one-time").on("change", function() {
    var validity = validateDateTime(false);
    if (validity == "warning") {
        $("#one-time-schedule-warning").stop(true, true).slideDown(300);
        $("#one-time-schedule-error").stop(true, true).slideUp(300);
    } else if (validity == "invalid") {
        $("#one-time-schedule-warning").stop(true, true).slideUp(300);
        $("#one-time-schedule-error").stop(true, true).slideDown(300);
    } else {
        $("#one-time-schedule-warning, #one-time-schedule-error").stop(true, true).slideUp(300);
    }
});


/* gets test users from input */
$(document).on("keydown blur", "#test-user-input", function(e) {
    var code = e.keyCode || e.which;
    if (code == 9 || code == 13) { // 9: tab, 13: enter
        // prevent default tab or enter action
        e.preventDefault();
        // blur away
        $(this).blur();
    } else if (code === 0) { // 0: blur
        // if changes were made
        if ($(this).val().trim() !== "") {
            checkTestUser($(this).val());
        } else {
            $(this).val("");
        }
    }
});


/********** this block also exists exactly the same way in survey_builder.js **********/
/* toggles default value example */
$("#toggle-default-value-example").on("click", function(e) {
    // if hidden
    if ($("#default-value-example").css("display") == "none") {
        // show example
        $("#default-value-example").slideDown(250);
        // change this text
        $(this).text("Hide example...");
    // if shown
    } else {
        // show example
        $("#default-value-example").slideUp(250);
        // change this text
        $(this).text("View example...");
    }
})
/********** /this block also exists exactly the same way in survey_builder.js **********/


/**************************************
 * Functions
 **************************************/
/* submits item for creation */
function addItem() {
    var cohortId = $("#cohort-id").val();
    var data;
    var itemType = $("#add-new-item .nav-tabs .active a").data("item-type");
    var parentId = $("#new-item-parent-id").val();
    var parentType = $("#new-item-parent-type").val();
    // get data
    if (itemType == "set_attribute") {
        var attributeName = $("#set-attribute-field-new").val().trim();
        var attributeValue = $("#set-attribute-value-new").val().trim();
        // error handling
        if (!attributeName) {
            alert("Please select an attribute to set.");
            return false;
        }
        if (!attributeValue) {
            alert("Please enter a value for '" + attributeName + "' to be set to.");
            return false
        }
        data = {
            "attribute_name": attributeName,
            "attribute_value": attributeValue
        };
    } else if (itemType == "conditional") {
        var attribute = $("#conditional-field-new").val().trim();
        var comparison = $("#conditional-value-new").val().trim();
        var upperRange = $("#conditional-range-new").val().trim();
        var comparisonIsAttribute = $("#comparison-is-attribute").prop("checked");
        var subtype = $("#conditional-subtype").val()
        // error handling
        if (!attribute) {
            alert("Please select an attribute to use.");
            return false;
        }
        if ($("#conditional-field-answer").val() == ANSWER_VALUE && !validateMultipleChoices([comparison])) {
            return false
        };
        data = {
            "attribute": attribute,
            "comparison": comparison,
            "upper_range": upperRange,
            "comparison_is_attribute": comparisonIsAttribute,
            "subtype": subtype
        };
    } else if (itemType == "send_message") {
        var messageText = $("#new-message-text").val().trim();
        // error checking
        if (messageText == "") {
            alert("Please enter your message text.")
            return false;
        }
        data = {
            "text": messageText
        };
    } else if (itemType == "send_question") {
        data = editQuestion(true);
        if (data == false) {
            return false;
        }
    } else {
        window.alert("ERROR: New item type is invalid");
        return false;
    }
    showStatus(function() {
        // hide modal
        $("#add-new-item").modal("hide");
        // submit data
        post("/create_new_item", {
            "data": JSON.stringify(data),
            "cohort_id": cohortId,
            "type": itemType,
            "parent": parentId,
            "parent_type": parentType
        }, true);
        return $.Deferred();
    }, "Creating new item", "Item created", "Error: Unable to create new item");
}


/* submits schedule for update/creation */
function addSchedule() {
    var cohort_id = $("#cohort-id").val();
    var data;
    var resend_quantity = parseInt($("#resend-number").val().trim(), 10);
    var resend_hour = 20;
    var resend_type = $("input[name='resend-radio']:checked").val();
    var schedule_id = $("#schedule-id").val();
    var subtype = $("#add-schedule .nav-tabs .active a").data("subtype");
    if (isNaN(resend_quantity)) {
        alert('Please enter a number for "Resend how many times?"');
        return false;
    }
    if (resend_type == "hours") {   
        resend_hour = parseInt($("#resend-interval").val().trim());
    } else {
        resend_hour = parseInt($("#resend-hour").val().trim());
    }
    data = {
        "cohort_id": cohort_id,
        "resend_hour": resend_hour,
        "resend_quantity": resend_quantity,
        "resend_type": resend_type,
        "subtype": subtype
    };
    // get data
    if (subtype == "recurring") {
        var day_numbers = [];
        var send_hour_recurring = $("#send-hour-recurring").val();
        // get days of week
        for (var i = 0, len = DAYS_OF_WEEK.length; i < len; i++) {
            if ($("#" + DAYS_OF_WEEK[i]).prop("checked") == true) {
                day_numbers.push(i);
            }
        }
        // check if no days have been selected
        if (day_numbers.length == 0) {
            alert("Please select which days of the week you would like the schedule to run.");
            return false;
        }
        data = $.extend(data, {
            "send_hour": parseInt(send_hour_recurring, 10),
            "question_days_of_week": day_numbers
        });
    } else if (subtype == "one_time") {
        var date = $("#schedule-date").val();
        var send_hour_one_time = $("#send-hour-one-time").val();
        // check that they entered a date
        if (date == "") {
            alert("Please select a date.")
            return false;
        }
        // check date/time is after current time
        if (validateDateTime(true) == "invalid") {
            return false;
        };
        data = $.extend(data, {
            "send_hour": parseInt(send_hour_one_time, 10),
            "date": date
        });
    } else if (subtype == "on_user_creation") {
        // no data to add
    } else {
        alert("Error: No schedule subtype found");
        return false;
    }
    showStatus(function() {
        // hide add schedule modal and show loading modal
        $("#add-schedule").modal("hide");
        // submit data
        if (schedule_id) {
            post("/modify_item", {
                "cohort_id": cohort_id,
                "data": JSON.stringify(data),
                "type": "schedule",
                "item_id": schedule_id
            }, true);
        } else {
            post("/create_new_item", {
                "cohort_id": cohort_id,
                "data": JSON.stringify(data),
                "type": "schedule"
            }, true);
        }
        return $.Deferred();
    }, "Creating new schedule", "New schedule created", "Error: unable to create new schedule");
}


/********** this block also exists exactly the same way in user_management.js **********/
/* submits new user attribute for creation */
function addUserAttribute() {
    var cohortId = $("#cohort-id").val();
    var defaultValue = $("#default-value").val().trim();
    var newAttributeName = $("#attribute-name").val().trim();
    // error checking
    if (newAttributeName == "") {
        alert("Please enter an attribute name.");
        return false;
    }
    if (newAttributeName.charAt(0) == "$") {
        alert("Sorry, attribute names cannot begin with the character '$'.")
        return false;
    }
    if (newAttributeName.indexOf(".") >= 0) {
        alert("Sorry, periods '.' are not allowed in attribute names. Underscores are recommended " +
              "instead: '" + newAttributeName.replace(/\./g, "_") + "'")
        return false;
    }
    if ($.inArray(newAttributeName.toLowerCase(), FORBIDDEN_CUSTOM_ATTRIBUTES) > -1) {
        alert("Sorry, but certain single word keywords are not permitted: '" + FORBIDDEN_CUSTOM_ATTRIBUTES.join(', ') + "'.");
        return false;
    }
    // close modal
    $("#add-attribute").modal("hide");
    // set up submit data
    data = {
        "cohort_id": cohortId,
        "new_attribute": newAttributeName.toLowerCase().trim(),
        "default_value": defaultValue.trim()
    }
    // submit
    showStatus(function() {
        // submit data
        post("/create_user_attribute", data, true);
        return $.Deferred();
    }, "Creating user attribute", "User attribute created", "Error: Unable to create new user attribute");
}
/********** /this block also exists exactly the same way in user_management.js **********/

function copySchedule() {
    // make happy variables
    var scheduleId = $("#schedule-id").val();
    var newCohortId = $("#other-cohort").val().trim();

    // have a way to hide or close modal
    $("copy-schedule").modal("hide");

    showStatus(function() {
    // submit data
        post("/copy_survey", {
        //"new_cohort": new_cohort,
            "schedule_id": scheduleId,
            "new_cohort_id": newCohortId
        }, true);
        return $.Deferred();
    }, "Copying Schedule", "Schedule copied", "Error: Unable to copy schedule");

}


/* copies all schedules in the cohort */
function copyAllSchedules() {
    var newCohortId = $("#other-cohort-a").val().trim();
    var oldCohortId =  $("#cohort-id").val();

    // have a way to hide or close modal
    $("copy-all-schedules").modal("hide");
    
    showStatus(function() {
    // submit data
        post("/copy_all_surveys", {
        //"new_cohort": new_cohort,
            "old_cohort_id": oldCohortId,
            "new_cohort_id": newCohortId
        }, true);
        return $.Deferred();
    }, "Copying Schedules", "Schedules copied", "Error: Unable to copy schedules");

}


/* delete action and its children */
function deleteActionAndChildren() {
    // submit data
    var itemId = $("#primary-delete").val();
    var parent = $("#" + itemId).attr("data-parent");
    var type = $("#primary-delete-type").val();
    var parentType = $("#primary-delete-parent-type").val();
    var cohortId = $("#cohort-id").val();
    // hide modal
    $("#confirm-delete").modal("hide");
    showStatus(function() {
        // submit data
        post("/delete_item", {
            "cohort_id": cohortId,
            "item_id": itemId,
            "item_type": type,
            "parent": parent,
            "parent_type": parentType
        }, true);
        return $.Deferred();
    }, "Deleting item", "Item deleted", "Error: Unable to delete item");
}


/* submits data for editing questions */
function editQuestion(returnData) {
    var cohortId = $("#cohort-id").val();
    var itemId = $("#item-to-be-edited-id").val();
    var parentId = $("#new-item-parent-id").val();
    var parentType = $("#new-item-parent-type").val();
    var parser = $("#new-question-type").val();
    var questionText = $("#new-question-text").val().trim();
    // error checking
    if (questionText == "") {
        alert("Please enter your question text.")
        return false;
    }
    // set data
    data = {
            "auto_append": false, // prevents showing auto-append after changing to a non-multiple-choice question type
            "text": questionText.trim(),
            "parser": parser
           };
    // if question type is multiple choice
    if (parser == "multiple_choice_parser") {
        var autoAppend = $("#auto-append").prop("checked");
        var choiceValues = [];
        var numberOfChoices = parseInt($("#number-of-choices").val(), 10);
        // error handling
        if (numberOfChoices < 1) {
            alert("Please enter at least one choice.")
            return false;
        }
        $("#multiple-choices input").each(function() {
            choiceValues.push($(this).val().trim());
        });
        if (!validateMultipleChoices(choiceValues)) {
            return false;
        }
        // append data
        data = $.extend(data, {
            "auto_append": autoAppend,
            "choices": numberOfChoices,
            "choices_text": choiceValues,
            "resend": MULTIPLE_CHOICE_RESEND_TEXT
        });
    // if question type is numeric
    } else if (parser == "number_parser") {
        var min = parseInt($("#minimum-answer-value").val(), 10);
        var max = parseInt($("#maximum-answer-value").val(), 10);
        // error checking
        if (max > 2147483647 || min > 2147483647) { // 2^31 - 1, largest int supported in python (before it becomes long)
            alert("Please enter a value less than 2147483648.");
            return false;
        }
        if (min < 0 || max < 0) { // we currently don't parse negative numbers
            alert("Please enter a positive value.")
            return false;
        }
        // append data
        data = $.extend(data, {
            "min": min,
            "max": max,
            "resend": "Please answer again with a number between " + min + " and " + max + "."
        });
    // if question type is yes or no
    } else if (parser == "yes_or_no_parser") {
        // append data
        data = $.extend(data, {
            "resend": "Please answer yes or no."
        });
    // if question type is open_ended (at the moment, that's all we have left)
    } else {
        // append data
        data = $.extend(data, {
            "resend": null
        });
    }
    // if returnData is requested, return data
    if (returnData) {
        return data;
    }
    // submit
    post("/modify_item", {
        "data": JSON.stringify(data),
        "cohort_id": cohortId,
        "type": "send_question",
        "item_id": itemId,
        "parent": parentId,
        "parent_type": parentType
    }, true);
}


/********** this block also exists exactly the same way in user_management.js **********/
/* launch add attribute modal */
function launchAddAttribute() {
    // reset all values in modal
    resetInputs("add-attribute", [{"id": "resend-checkbox", "default": true}]);
    // set modal properties
    setModalProperties("add-schedule", {
        "title": "Add Attribute",
        "button": "Add Attribute"
    });
    // show modal
    $("#add-attribute").modal("show");
}
/********** /this block also exists exactly the same way in user_management.js **********/


/* launch add item modal */
function launchAddItem(newItemParentId, newItemParentType, parser) {
    // reset all values and views in modal
    resetInputs("add-new-item", [
        {"id": "number-of-choices", "default": 3},
        {"id": "multiple-choices", "html": "<input class='form-control multiple-choice-answer-choice' />"},
        {"id": "minimum-answer-value", "default": 1},
        {"id": "maximum-answer-value", "default": 5},
        {"id": "conditional-field-new", "default": ""},
        {"id": "set-attribute-field-new", "default": ""},
        {"id": "set-attribute-value-answer", "default": ANSWER_VALUE_DISPLAY},
        {"id": "conditional-value-new-select", "html": ""},
        {"id": "conditional-range-new-select", "html": ""},
        {"id": "new-question-type", "default": "open_ended"},
        {"id": "auto-append", "default": true},
        {"id": "conditional-subtype", "default": "exactly"}
    ]);
    $("#new-conditional-input-warning, #conditional-value-new, #set-attribute-value-new, .non-attr-values").show();
    $("#new-conditional-input, #conditional-field-answer, #conditional-value-new-select, #conditional-range-new-select, #set-attribute-value-answer, #set-attribute-value-status, .attr-values").hide();
    $("#conditional-field-new, #set-attribute-value-new, #conditional-subtype").prop("disabled", false);
    // set modal properties
    setModalProperties("add-new-item", {
        "title": "Add New Item",
        "button": "Add New Item",
        "buttonAction": "addItem()"
    });
    // depending on parser, show only some or all of the item types
    if (!parser) {
        // if no parser, show all options
        showAllHideAll("#add-new-item .nav-tabs li", false, "show");
        // show tab
        $("#add-new-item .nav-tabs a[href='#new-question']").tab("show");
    } else {
        // if no parser, hide new question and new message
        showAllHideAll("#add-new-item .nav-tabs li", ".hide-if-parser", "show");
        // show tab
        $("#add-new-item .nav-tabs a[href='#new-conditional']").tab("show");
    }
    // if we're adding an item from a question, we want to hide warning and enforce using ANSWER_VALUE
    if (newItemParentType == "send_question") {
        // don't need to show warning for conditionals/set attribute since we enforce using ANSWER_VALUE
        $("#new-conditional-input-warning").hide();
        $("#new-conditional-input").show();
        // enforce using ANSWER_VALUE
        $("#conditional-field-new").val(ANSWER_VALUE).prop("disabled", true);
        $("#set-attribute-value-new").val(ANSWER_VALUE).hide();
        $("#set-attribute-value-answer").show();
        $("#conditional-field-answer, #conditional-field-answer").show();
        // if parser is not open_ended, switch to showing the selects
        if (parser != "open_ended") {
            setConditionalValueSelect(newItemParentId, parser);
            $("#conditional-value-new-select").show();
            $("#conditional-range-new-select").show();
            $("#conditional-value-new").hide();
            $("#conditional-range-new").hide();
        } else {
            $("#conditional-value-new-select").hide();
            $("#conditional-range-new-select").hide();
            $("#conditional-value-new").show();
            $("#conditional-range-new").show();
        }
        if (parser != "number_parser") {
            $("#conditional-subtype").prop("disabled", true)
        } else {
            $("#conditional-subtype").prop("disabled", false)
        }
    }
    // populate values
    $("#new-item-parent-id").val(newItemParentId);
    $("#new-item-parent-type").val(newItemParentType);
    // show modal
    $("#add-new-item").modal("show");
}


/* launches add schedule modal */
function launchAddSchedule() {
    // reset all values in modal
    resetInputs("add-schedule", [
        {"id": "resend-number", "default": 0},
        {"id": "resend-hour", "default": 12}
    ]);
    $("input[name=resend-radio][value='time']").prop("checked",true).change();
    // set modal properties
    setModalProperties("add-schedule", {
        "title": "Add Schedule",
        "button": "Add Schedule"
    });
    // show modal
    $("#add-schedule").modal("show");
}

/* launches copy schedule modal */
function launchCopySchedule(scheduleId) {
    // reset modal
    $("#schedule-id").val(scheduleId);

    //populate hidden inputs
    setModalProperties("copy-schedule", {
        "title": "Copy Schedule",
        "button": "Copy Schedule",
        "buttonAction": "copySchedule()"
    });

    $("#copy-schedule").modal("show");
}

/*launches copy all schedules modal */
function launchCopyAllSchedules(cohortId) {
    // reset modal
    $("#cohort-id-a").val(cohortId);

    //populate hidden inputs
    setModalProperties("copy-all-schedules", {
        "title": "Copy All Schedules",
        "button": "Copy All Schedules",
        "buttonAction": "copyAllSchedules()"
    });

    $("#copy-all-schedules").modal("show");
}


/* launches delete element modal */
function launchDeleteElement(clickedElement, elementId, elementType, elementParentType) {
    // reset modal
    resetInputs("confirm-delete", [{"id": "to-delete", "html": ""}]);
    // populate hidden inputs
    $("#primary-delete").val(elementId);
    $("#primary-delete-type").val(elementType);
    $("#primary-delete-parent-type").val(elementParentType);
    // get html for action to delete and its children and populate to modal
    $("#to-delete").html(clickedElement.closest(".action-level").closest(".action-level").html());
    // remove all action-related html and classes so we leave only description html
    var htmlToRemove = [
                        ".schedule-toggle",
                        ".button-block",
                        ".alert"
                       ];
    for (var i = 0, len = htmlToRemove.length; i < len; i++) {
        $("#to-delete").find(htmlToRemove[i]).remove();
    }
    // disable fields so users can't change them
    $("#to-delete").find("[contenteditable], input, select, div, span")
        .prop("disabled", true)
        .addClass(
            "reset-cursor " +
            "no-hover " +
            "no-underline"
        )
        .removeAttr(
            "id " +
            "contenteditable " +
            "data-parent " +
            "data-index " +
            "data-parent-type " +
            "data-parent-2 " +
            "data-this " +
            "data-type " +
            "data-parser " +
            "onchange " +
            "onclick "
        );
    // show modal
    $("#confirm-delete").modal("show");
}


/* launches edit question modal */
function launchEditQuestion(itemId, parent, parent_type, parser, choices) {
    // reset all values in modal
    resetInputs("add-new-item", [{"id": "multiple-choices", "default": "<input class='form-control multiple-choice-answer-choice' />"}]);
    // set modal properties
    setModalProperties("add-new-item", {
        "title": "Edit Item",
        "button": "Edit Item",
        "buttonAction": "editQuestion()"
    });
    // hide all tabs except questions
    showAllHideAll("#add-new-item .nav-tabs li", ".hide-if-edit-question", "show");
    // repopulate items
    $("#new-question-text").val($("#" + itemId + "-text").text());
    $("#item-to-be-edited-id").val(itemId);
    $("#new-item-parent-id").val(parent);
    $("#new-item-parent-type").val(parent_type);
    $("#new-question-type").val(parser);
    $("#number-of-choices").val(choices);
    $("#minimum-answer-value").val($("#" + itemId + "-min").val());
    $("#maximum-answer-value").val($("#" + itemId + "-max").val());
    // auto-append
    if ($("#" + itemId + "-auto-append").length > 0) {
        $("#auto-append").prop("checked", true);
    }
    // multiple choice answer choices
    if (parser == "multiple_choice_parser") {
        var choiceInputsToWrite = "";
        $("#" + itemId + "-choices input").each(function() {
            choiceInputsToWrite += "<input class='form-control multiple-choice-answer-choice' value='" + $(this).val() + "' />";
        });
        $("#multiple-choices").html(choiceInputsToWrite);
    }
    // show only the relevant divs for the selected parser
    showAllHideAll("#new-question div[data-parser='" + parser + "']", "#multiple-choice-settings, #numeric-settings", "hide")
    // navigate to question tab
    $("#add-new-item .nav-tabs a[href='#new-question']").tab("show");
    // show modal
    $("#add-new-item").modal("show");
}


/* launches edit schedule modal */
function launchEditSchedule(scheduleId) {
    // reset all values in modal
    resetInputs("add-schedule", [
        {"id": "resend-number", "default": 0},
        {"id": "resend-hour", "default": 12}
    ]);
    // set modal properties
    setModalProperties("add-schedule", {
        "title": "Edit Schedule",
        "button": "Edit Schedule"
    });
    // repopulate items
    var modalTabToShow;
    var scheduleSubtype = $("#" + scheduleId + "-subtype").val();
    var resendNumber = $("#" + scheduleId + "-resend-number").text();
    var resendType = $("#" + scheduleId + "-resend-type").text();
    if (resendNumber === 0) {
        $("input[name=resend-radio][value='none']").prop("checked",true).change();
    } else if (resendType == "time") {
        $("input[name=resend-radio][value='time']").prop("checked",true).change();
        $("#resend-number").val(resendNumber);
        $("#resend-hour").val($("#" + scheduleId + "-resend-hour").text());       
    } else if (resendType == "hours") {
        $("input[name=resend-radio][value='hours']").prop("checked",true).change(); 
        $("#resend-number").val(resendNumber);
        $("#resend-interval").val($("#" + scheduleId + "-resend-interval").text());   
    }
    $("#schedule-id").val(scheduleId);
    $("#schedule-subtype").val(scheduleSubtype);
    if (scheduleSubtype == "recurring") {
        modalTabToShow = "schedule-recurring";
        $("#send-hour-one-time").val($("#" + scheduleId + "-send-hour").text());
        $("#send-hour-recurring").val($("#" + scheduleId + "-send-hour").text());
        // repopulate days of week
        var days = $("#" + scheduleId + "-date").text().trim().split(",");
        days.pop(); // pop out the last item (empty, caused by trailing comma)
        for (var i = 0, len = days.length; i < len; i++) {
            days[i] = days[i].trim(); // remove whitespace
            $("#" + days[i]).prop("checked", true);
        }
    } else if (scheduleSubtype == "one_time") {
        modalTabToShow = "schedule-one-time";
        $("#schedule-date").val($("#" + scheduleId + "-date").text());
        $("#send-hour-one-time").val($("#" + scheduleId + "-send-hour").text());
        $("#send-hour-recurring").val($("#" + scheduleId + "-send-hour").text());
    } else if (scheduleSubtype == "on_user_creation") {
        modalTabToShow = "schedule-on-user-creation";
    } else {
        window.alert("Error: Schedule type invalid");
    }
    // show modal
    $("#add-schedule").modal("show");
    // show tab
    $("#add-schedule .nav-tabs a[href='#" + modalTabToShow + "']").tab("show");
}


/* launches manually-run schedule modal */
function launchManuallyRunSchedule(scheduleId) {
    // set modal properties
    setModalProperties("manually-run-schedule", {
        "title": "Manually Run Schedule",
        "buttonHref": "/manually_run_schedule/" + scheduleId
    });
    // show modal
    $("#manually-run-schedule").modal("show");
}

/* launches test schedule modal */
function launchTestSchedule(scheduleId) {
    //set modal properties
    setModalProperties("test-schedule", {
        "title": "Test Schedule",
        "buttonAction": "testSchedule('" + scheduleId + "')"
    });
    $("#test-users").empty();
    // show modal
    $("#test-schedule").modal("show");
}


/* passes the information for testing to backend */
function testSchedule(scheduleId) {
    var users = [];
    $(".test-user-to-add").each(function () {
        users.push($(this).text());
    });
    users = JSON.stringify(users);
    $("#test-schedule").modal("hide");
    return post ("/test_schedule", {
        "users": users,
        "schedule_id": scheduleId
    }, false);
}

/* moves an element and its children above the preceding element and their children */
function moveItem(direction, itemId, parentId, parentType) {
    showStatus(function() {
        var $this = $("#" + itemId);
        var currentIndex = parseInt($this.attr("data-index"), 10);
        var cohortId = $("#cohort-id").val();
        var newIndex = (direction == "up") ? (currentIndex - 1) : (currentIndex + 1);
        if (
            // if direction is up and item isn't at the top
            (direction == "up" && currentIndex > 0) ||
            // if direction is down and item isn't at the bottom
            (direction == "down" && ($this.siblings(".action-level[data-index='" + newIndex + "']").length > 0))
           ) {
            // submit data
            return post("/move_action", {
                "cohort_id": cohortId,
                "direction": direction,
                "index": currentIndex,
                "parent": parentId,
                "parent_type": parentType
            }, false)
            // iff successful, show animation and reset data-index
            .done(function() {
                var itemToSwapWith = $this.siblings(".action-level[data-index='" + newIndex + "']");
                // set new index for both
                $this.attr("data-index", newIndex);
                itemToSwapWith.attr("data-index", currentIndex);
                // animate
                $this.fadeOut(function() {
                    (direction == "up") ? $this.insertBefore(itemToSwapWith) : $this.insertAfter(itemToSwapWith);
                    $this.fadeIn();
                });
            });
        } else {
            // return message that it's already at the top or bottom
            var position = (direction == "up") ? "top" : "bottom";
            return $.Deferred().resolve("Item already at the " + position + " of its level");
        }
    }, "Moving", "Saved", "Error: Item not moved");
}


/* dynamically-sized selects */
function resizeSelects(element) {
    $(element).each(function() {
        if ($(this).attr("id") != "selectWidthCalculator") {
            // populate text value of element into hidden select
            $("#selectWidthCalculatorOption").html($("option:selected", this).text().trim());
            // reset hidden select width
            $("#selectWidthCalculator").width("auto");
            // set element width
            $(this).width($("#selectWidthCalculator").width());
        }
    })
}


/* save contenteditable changes to database */
function saveContent(element) {
    var cohortId = $("#cohort-id").val();
    var data;
    var itemId = element.attr("data-this");
    var itemType = element.attr("data-type");
    var newText = element.text().trim().replace("\xa0", " ");
    var parent = element.attr("data-parent");
    var parentType = element.attr("data-parent-type");
    // error checking
    if (itemType == "send_question" || itemType == "send_message") {
        // disallow SMS over 160 characters
        if (newText.length > MAX_SMS_LENGTH) {
            alert("Please enter a message with fewer than " +  MAX_SMS_LENGTH + " characters. This message has NOT been saved.")
            return false;
        }
    }
    // set data based on item type
    if (itemType == "send_question") {
        var parser = element.attr("data-parser");
        data = {
            "text": newText,
            "parser": parser
        };
    } else if (itemType == "send_message") {
        data = {
            "text": newText
        };
    } else if (itemType == "conditional") {
        var attributeText = $("#" + itemId + "-attribute").val() || $("#" + itemId + "-attribute").text().trim();
        var comparisonText = $("#" + itemId + "-comparison").val() || $("#" + itemId + "-comparison").text().trim();
        var subtype = $("#" + itemId + "-conditional-subtype").val() || $("#" + itemId + "-conditional-subtype").text().trim();
        var upperRange = $("#" + itemId + "-upper-range").val() || $("#" + itemId + "-upper-range").text().trim();
        if (subtype == 'range') {
            $("#" + itemId + "-range-div").removeClass("hidden");
            $("#" + itemId + "-range-div").addClass("range-div");
        } else {
            $("#" + itemId + "-range-div").addClass("hidden");
            $("#" + itemId + "-range-div").removeClass("range-div");
        }
        data = {
            "attribute": attributeText,
            "comparison": comparisonText,
            "upper_range": upperRange,
            "subtype": subtype
        };
    } else if (itemType == "set_attribute") {
        var attributeName = $("#" + itemId + "-attribute").val().trim();
        var attributeValue = $("#" + itemId + "-value").text().trim();
        data = {
            "attribute_name": attributeName,
            "attribute_value": attributeValue
        };
    }
    // wrap with showStatus to show user status of request
    showStatus(function() {
        // save data
        return post("/modify_item", {
            "data": JSON.stringify(data),
            "cohort_id": cohortId,
            "type": itemType,
            "item_id": itemId,
            "parent": parent,
            "parent_type": parentType
        }, false);
    }, "Saving", "Saved", "Error: Not saved");
}


/* sets options for conditionals/set attributes in response to a question and enforces using ANSWER */
function setConditionalValueSelect(itemId, parser) {
    $this = $("#conditional-value-new-select");
    // if multiple choices
    if (parser == "multiple_choice_parser") {
        // gather choices inputs and rewrite them as options
        var choicesToWrite = "";
        $("#" + itemId + "-choices input").each(function() {
            choicesToWrite += "<option value='" + $(this).val() + "'>" + $(this).val() + "</option >";
        });
        // replace options into selects and set default to blank
        $this.html(choicesToWrite).val("");
    } else if (parser == "number_parser") {
        var min = $("#" + itemId + '-min').val();
        var max = $("#" + itemId + '-max').val();
        // create options from min to max
        var optionsToWrite = "";
        for (var i = min; i <= max; i++) {
            optionsToWrite += "<option value='" + i + "'>" + i+ "</option>";
        }
        // write options and default to ""
        $this.html(optionsToWrite).val("");
        $("#conditional-range-new-select").html(optionsToWrite).val("");
    } else if (parser == "yes_or_no_parser") {
        // options yes and no
        var optionsToWrite = "<option value='yes'>Yes</option><option value='no'>No</option>";
        // write options
        $this.html(optionsToWrite);
        // default to ""
        $("#conditional-value-new-select, #set-attribute-value-new-select").val("");
    }
}


/* toggles syntax highlighting */
function toggleSyntaxHighlighting() {
    // get current status ("on" or "off")
    var currentStatus = $("#surveys").attr("data-syntax-highlighting")
    // if "off", toggle on highlighting
    if (currentStatus == "off") {
        // highlight syntax
        $(".message, .question").css("color", "#771691");
        $(".action, .conditional").css("color", "#ea4f21");
        $(".point:not(.clickable)").css("color", "#077c0e");
        // toggle current status
         $("#surveys").attr("data-syntax-highlighting", "on")
    // else if "on", toggle off highlighting
    } else if (currentStatus == "on") {
        // set text to gray-black
        $(".message, .question, .action, .conditional, .point:not(.clickable)").css("color", "#373737");
        // toggle current status
        $("#surveys").attr("data-syntax-highlighting", "off")
    }
}


/* changes number of answer choices for a multiple choice question */
function updateMultipleChoiceInputs() {
    var numberOfDesiredChoices = parseInt($("#number-of-choices").val(), 10);
    var choicesInputs = "";
    var currentNumberOfChoices = $(".multiple-choice-answer-choice").length;
    // error checking
    if (numberOfDesiredChoices <= 0) {
        alert("Please enter a number of choices that is at least 1.");
        return false;
    }
    // if we have fewer than desired, append new ones until we reach that number
    if (currentNumberOfChoices < numberOfDesiredChoices) {
        for (var i = currentNumberOfChoices; i < numberOfDesiredChoices; i++) {
            choicesInputs += "<input class='form-control multiple-choice-answer-choice' />";
        }
        $("#multiple-choices").append(choicesInputs);
    // if we have more than desired, delete new ones until we reach that number
    } else if (currentNumberOfChoices > numberOfDesiredChoices) {
        while($(".multiple-choice-answer-choice").length > numberOfDesiredChoices) {
            $(".multiple-choice-answer-choice:last").remove();
        }
    }
}


/* check if date/time is in paste */
function validateDateTime(showAlerts) {
    var date = $("#schedule-date").val();
    var send_hour_one_time = $("#send-hour-one-time").val();
    // if there is no date, no problem
    if (!date) {
        return "valid";
    }
    if (send_hour_one_time.length == 1) { // correct padding for selectedTime parsing
        send_hour_one_time = "0" + send_hour_one_time;
    }
    // get current time values in ms
    var currentTimeUTC = new Date().getTime(); // UTC
    var oldestTime = currentTimeUTC - 11 * 60 * 60 * 1000; // UTC-11
    var newestTime = currentTimeUTC + 14 * 60 * 60 * 1000; // UTC+14
    // get selected time (casted as UTC)
    var selectedTime = Date.parse(date + "T" + send_hour_one_time + ":00:00.000Z"); // yyyy-mm-ddThh:00:00.000Z (the T is required for proper parsing)
    // if selectedTime is before oldestTime, this has already passed everywhere on Earth
    if (selectedTime < oldestTime) {
        if (showAlerts) {
            alert("Error: Please select a future date and time.");
        }
        return "invalid";
    // if selectedTime is after oldestTime but before newestTime, this potentially has passed for some users
    } else if (selectedTime < newestTime) {
        if (showAlerts) {
            alert("Warning: This date and time may have already passed for some users depending on their timezone.\n\nPlease click 'OK' to continue.");
        }
        return "warning";
    // if selectedTime is after newestTime, it's a future date/time
    } else {
        return "valid";
    }
}


/* validates an array of answer choices to enforce no blank or single word keywords */
function validateMultipleChoices(choices) {
    for (var i = 0; i < choices.length; i++) {
        if ($.inArray(choices[i].toLowerCase(), [""]) > -1) {
            alert("Blank responses are not permitted.");
            return false;
        }
        if ($.inArray(choices[i].toLowerCase(), FORBIDDEN_MULTIPLE_CHOICE_ANSWERS) > -1) {
            alert("Sorry, but certain single word keywords are not permitted: '" + FORBIDDEN_MULTIPLE_CHOICE_ANSWERS.join(', ') + "'.");
            return false;
        }
        if (/\[\[|\[\[ |\]\]| \]\]/.test(choices[i])) {
            alert("Sorry, merge fields are not permitted answer choices.");
            return false;
        }
    }
    return true;
}

/* checks that the test user being added exists */
function checkTestUser(phonenum) {
    numbers = window.COHORT_USER_NUMBERS;
    phonenum = phonenum.trim();
    existing = [];
    $(".test-user-to-add").each(function () {
        existing.push($(this).text());
    });
    if (numbers.indexOf(phonenum) == -1) {
        alert("You are attempting to add an invalid test user!");
    } else if (existing.indexOf(phonenum) !== -1) {
        $("#test-user-input").val("");
    } else {
        newNum = "<p class='test-user-to-add'>" + phonenum + "</p>";
        $("#test-users").append(newNum);
        $("#test-user-input").val(""); 
    }
}

/* checks if a new Set Attribute is checking status */
function setStatusCheck(element="None") {
    if (element == "None") {
        if ($("#set-attribute-field-new").val() == "status") {
            $("#set-attribute-value-new").hide();
            $("#set-attribute-value-status").show();
            $("#set-attribute-value-status").val("active");  
            $("#set-attribute-value-new").val("active");         
        } else {
            $("#set-attribute-value-new").show();
            $("#set-attribute-value-status").hide();                 
        }
    } else {
        attr = "#" + element + "-attribute";
        val = "#" + element + "-value";
        stat = "#" + element + "-status";
        if ($(attr).val() == "status") {
            $(val).addClass("status-hide").hide();
            $(stat).removeClass("status-hide").show();
            $(val).text($(stat).val());         
        } else {
            $(val).removeClass("status-hide").show();
            $(stat).addClass("status-hide").hide();            
        }
        saveContent($(attr));
    }
}

/* keeps status drop down coordinated with new field value */
function setNewStatus(element="None") {
    if (element == "None") {
        $("#set-attribute-value-new").val($("#set-attribute-value-status").val());          
    } else {
        attr = "#" + element + "-attribute";
        val = "#" + element + "-value";
        stat = "#" + element + "-status";
        $(val).text($(stat).val());
        saveContent($(attr));        
    }
}

/* changes add-new-item modal depending on conditional type */
function conditionalSubtypeChange() {
    if ($("#conditional-subtype").val() == 'range') {
        $("#conditional-range-div").removeClass("hidden");
        $("#conditional-range-div").addClass("range-div");
    } else {
        $("#conditional-range-div").addClass("hidden");
        $("#conditional-range-div").removeClass("range-div");
    }
}

/* changes add-new-item modal depending on whether comparison type */
function comparisonIsAttributeChange() {
    if ($("#comparison-is-attribute").prop('checked')) {
        $(".non-attr-values").hide();
        $(".attr-values").show();
        $("#conditional-value-new-attr").val('');
        $("#conditional-range-new-attr").val('');  
    } else {
        $(".non-attr-values").show();
        $(".attr-values").hide(); 
        $("#conditional-value-new").val('');
        $("#conditional-range-new").val('');      
    }
}

/* switches whether or not a conditional compares to an attribute */
function launchEditConditional(element) {
    var itemId = element.attr("data-this");
    var parentId = element.attr("data-parent");
    var parentType = element.attr("data-parent-type");
    var attributeText = $("#" + itemId + "-attribute").val() || $("#" + itemId + "-attribute").text().trim();
    var comparisonText = $("#" + itemId + "-comparison").val() || $("#" + itemId + "-comparison").text().trim();
    var subtype = $("#" + itemId + "-conditional-subtype").val() || $("#" + itemId + "-conditional-subtype").text().trim();
    var upperRange = $("#" + itemId + "-upper-range").val() || $("#" + itemId + "-upper-range").text().trim();
    var comparisonIsAttribute = element.attr("data-value");
    var parser = $("#" + parentId + "-parser").val() || $("#" + parentId + "-parser").text().trim();
    // reset modal inputs
    resetInputs("add-new-item", [
        {"id": "conditional-field-new", "default": ""},
        {"id": "conditional-value-new-select", "html": ""},
        {"id": "conditional-range-new-select", "html": ""},
        {"id": "conditional-subtype", "default": "exactly"}
    ]);
    // set modal properties
    setModalProperties("add-new-item", {
        "title": "Edit Item",
        "button": "Edit Item",
        "buttonAction": "editConditional()"
    });
    // hide all tabs except conditional
    showAllHideAll("#add-new-item .nav-tabs li", ".hide-if-edit-conditional", "show");
    // navigate to conditional tab
    $("#add-new-item .nav-tabs a[href='#new-conditional']").tab("show");
    // populate values
    $("#new-item-parent-id").val(parentId);
    $("#new-item-parent-type").val(parentType);
    $("#item-to-be-edited-id").val(itemId);
    $("#conditional-field-new").val(attributeText);
    $("#conditional-subtype").val(subtype);
    $("#conditional-value-new").val(comparisonText);
    $("#conditional-range-new").val(upperRange);
    // if we're editing a conditional attached to a question, we want to hide warning and enforce using ANSWER_VALUE
    if (parentType == "question") {
        // don't need to show warning for conditionals since we enforce using ANSWER_VALUE
        $("#new-conditional-input-warning").hide();
        $("#new-conditional-input").show();
        // enforce using ANSWER_VALUE
        $("#conditional-field-new").val(ANSWER_VALUE).prop("disabled", true);
        $("#conditional-field-answer").show();
        // if parser is not open_ended, switch to showing the selects
        if (parser != "open_ended") {
            setConditionalValueSelect(parentId, parser);
            $("#conditional-value-new-select").val(comparisonText).show();
            $("#conditional-range-new-select").val(upperRange).show();
            $("#conditional-value-new").hide();
            $("#conditional-range-new").hide();
        } else {
            $("#conditional-value-new-select").hide();
            $("#conditional-range-new-select").hide();
            $("#conditional-value-new").show();
            $("#conditional-range-new").show();
        }
        if (parser != "number_parser") {
            $("#conditional-subtype").prop("disabled", true);
        } else {
            $("#conditional-subtype").prop("disabled", false);
        }
    } else {
        $("#conditional-value-new-select").hide();
        $("#conditional-range-new-select").hide();
        $("#conditional-value-new").show();
        $("#conditional-range-new").show();
    }
    // configure for checking against an attribute
    if (comparisonIsAttribute == "True") {
        $("#comparison-is-attribute").prop("checked", true);
        $("#conditional-value-new-attr").val(comparisonText);
        $("#conditional-range-new-attr").val(upperRange);
        $(".non-attr-values").hide();
        $(".attr-values").show();
    } else {
        $("#comparison-is-attribute").prop("checked", false);
        $(".non-attr-values").show();
        $(".attr-values").hide();
    }
    conditionalSubtypeChange();
    // launch modal
    $("#add-new-item").modal("show");
}

function editConditional () {
    var cohortId = $("#cohort-id").val();
    var itemId = $("#item-to-be-edited-id").val();
    var parentId = $("#new-item-parent-id").val();
    var parentType = $("#new-item-parent-type").val();
    var attribute = $("#conditional-field-new").val().trim();
    var comparison = $("#conditional-value-new").val().trim();
    var upperRange = $("#conditional-range-new").val().trim();
    var comparisonIsAttribute = $("#comparison-is-attribute").prop("checked");
    var subtype = $("#conditional-subtype").val();
    // error handling
    if (!attribute) {
        alert("Please select an attribute to use.");
        return false;
    }
    if ($("#conditional-field-answer").val() == ANSWER_VALUE && !validateMultipleChoices([comparison])) {
        return false;
    }
    // set data
    data = {
        "attribute": attribute,
        "comparison": comparison,
        "upper_range": upperRange,
        "comparison_is_attribute": comparisonIsAttribute,
        "subtype": subtype
    };
    // submit
    post("/modify_item", {
        "data": JSON.stringify(data),
        "cohort_id": cohortId,
        "type": "conditional",
        "item_id": itemId,
        "parent": parentId,
        "parent_type": parentType
    }, true);
}

/* angular stuff for autocompleting the test user search bar */
angular.module('testSchedUsers', []).controller("testSchedUsersCtrl", function ($scope) {
        $scope.testUsers = window.COHORT_USER_NUMBERS;
    })
.directive('autoComplete', function($timeout) {
        return function(scope, iElement, iAttrs) {
            iElement.autocomplete({
                appendTo: "#test-schedule",
                source: scope[iAttrs.uiItems],
                select: function() {
                    $timeout(function() {
                      iElement.trigger('input');
                    }, 0);
                }
            });
    };
});
