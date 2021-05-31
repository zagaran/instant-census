/**************************************
 * Constants
 **************************************/
var SCROLL_Y_HEIGHT_OFFSET = 324; // due to DOM loading stupidness (and laziness and figuring out a better way), set this manually by default
$(window).on("resize", function() {
    SCROLL_Y_HEIGHT_OFFSET = getScrollYHeightOffset();
});



/**************************************
 * $(window).load();
 **************************************/
/* Initialize dataTable */
window.usersDataTable;
$(window).load(function() {
    usersDataTable = $('#users').dataTable({
        "ajax": { // get data for table
            "data": {
                "cohort_id": $("#cohort-id").val()
            },
            "error": function() {
                $("#loading-container .text-center").html(
                    "Sorry, there was a problem loading the user management panel.<br /><br />" +
                    "<small>If reloading the page does not solve the problem, let us know at " +
                    "<a href='mailto:support@instantcensus.com' target='_blank'>" +
                    "support@instantcensus.com</a> and we'll take care of it!"
                );
            },
            "url": "/_get_users",
            "type": "POST"
        },
        "columnDefs": [
            {"orderable": false, "targets": 0}, // disable ordering on the first column
            {"type": "phoneNumber", "targets": 1}, // set phone number row type for search
        ],
        "createdRow": function(rowHTML, rowData, rowIndex) { // callback for each row created to add custom attributes
            // add these ONLY if cohort isn't completed since these allow changes
            if (!COHORT_COMPLETED) {
                // add contenteditable to all td except actions, status, and timezone (if valid status for changing)
                $("td", rowHTML).each(function() {
                    $(this).attr("contenteditable", "true");
                })
                $("td", rowHTML).eq(0).removeAttr("contenteditable"); // actions
                $("td", rowHTML).eq(2).removeAttr("contenteditable"); // status
                $("td", rowHTML).eq(3).removeAttr("contenteditable"); // timezone
                // add data-previous to all contenteditable
                $("td[contenteditable='true']", rowHTML).each(function() {
                    $(this).attr("data-previous", $(this).text());
                });
                // add attributes to phone number
                var userId = $("td", rowHTML).eq(0).children("a").attr("href").slice(-24);
                $("td", rowHTML).eq(1)
                    .addClass("editable")
                    .attr("data-column", "phonenum")
                    .attr("data-objid", userId);
                // add attributes to status
                var onclickFunction;
                if ($("#cohort-status").val() == "paused") {
                    onclickFunction = "launchChangeUserStatus('" + userId + "', true)";
                } else {
                    onclickFunction = "launchChangeUserStatus('" + userId + "')";
                }
                if (rowData[2] == "active" || rowData[2] == "paused" || rowData[2] == "inactive") {
                    $("td", rowHTML).eq(2)
                        .addClass("editable clickable")
                        .attr("id", userId + "-status")
                        .attr("onclick", onclickFunction);
                } else {
                    $("td", rowHTML).eq(2)
                        .addClass("data-table-disabled")
                        .attr("id", userId + "-status");
                }
                if (rowData[2] == "active") {
                    $("td", rowHTML).eq(2)
                        .attr("data-placement", "left")
                        .attr("data-toggle", "tooltip")
                        .attr("title", "Click to pause user (a paused user cannot reactivate themself and can only be reactivated by an administrator).");
                } else if (rowData[2] == "paused") {
                    $("td", rowHTML).eq(2)
                        .attr("data-placement", "left")
                        .attr("data-toggle", "tooltip")
                        .attr("title", "Click to activate user (a paused user cannot reactivate themself and can only be reactivated by an administrator).");
                } else if (rowData[2] == "inactive") {
                    $("td", rowHTML).eq(2)
                        .attr("data-placement", "left")
                        .attr("data-toggle", "tooltip")
                        .attr("title", "Click to activate user (an inactive user can also reactivate themself by texting back in).");
                }
                // add attributes to timezone (if enabled)
                if (TIMEZONE_SUPPORT) {
                    $("td", rowHTML).eq(3)
                        .addClass("editable")
                        .attr("data-objid", userId)
                        .attr("onclick", "launchChangeTimezone('" + userId + "', '" + rowData[1] + "', '" + rowData[3] + "')") // user id, phone number, current timezone
                        .css("cursor", "pointer");
                }
                // add attributes to the custom attributes
                $("td", rowHTML).slice(4).each(function() {
                    var attribute = $("#users thead th div").eq($(this).index()).text();
                    $(this)
                        .addClass("editable")
                        .attr("data-column", attribute)
                        .attr("data-objid", userId);
                });
            // if cohort completed, add these just for formatting purposes
            } else {
                $("td", rowHTML).eq(1)
                    .attr("data-column", "phonenum")
            }
        },
        "deferRender": true, // defer rendering to speed up initialization
        "fnDrawCallback": function() { // calls on draw event
            // re-enable tooltips to capture new ones created in table
            $(function () {
                $("#users [data-toggle='tooltip']").tooltip({container: "body"})
            })
        },
        "info": true, // enable bottom info ("Showing j to k of n entries")
        "initComplete": function() { // on dataTables loading completion
            // sticky left 2 columns
            new $.fn.dataTable.FixedColumns(usersDataTable, {
                leftColumns: 2
            });
            // resize dataTable to fix column header width issue
            usersDataTable.fnAdjustColumnSizing();
            $(".DTFC_LeftFootWrapper > .DTFC_Cloned > tfoot > tr > th").css("padding-right", 30); // fix for footer first column width
            // unbind search so that it only searches on "enter" or after 500ms
            $("#users_filter input").unbind();
            var searchTimer;
            $("#users_filter input").bind("keydown", function(e) {
                var code = e.keyCode || e.which;
                if (code == 13) { // 13: enter
                    // search
                    dataTableSearch(true);
                    usersDataTable.fnFilter($(this).val());
                    redrawDataTable();
                } else if (code == 9 || code == 27) { // 9: tab, 27: esc
                    // pass
                } else {
                    showStatus(function() {
                        var searchStatus = $.Deferred();
                        clearTimeout(searchTimer);
                        searchTimer = setTimeout(function() {
                            dataTableSearch(true);
                            redrawDataTable();
                            searchStatus.resolve("true");
                        }, 500);
                        return searchStatus;
                    }, "Searching", "Search complete", "Error: Something went wrong with our system");
                }
            });
            // hide loading div
            $("#loading-container").hide();
            $("#users-container").css("opacity", 1);
        },
        "language": {
            "search": "Filter by phone number:"
        },
        "paging": true, // enable pagination
        "pagingType": "simple_numbers", // setting for pagination controls
        "pageLength": 25, // default setting for how many users to display per page
        "processing": true,
        "renderer": "bootstrap", // set rendering of dataTables to be compatible with bootstrap styling
        "scrollX": true, // enable horizontal scrolling
        "scrollY": $(window).height() - SCROLL_Y_HEIGHT_OFFSET, // enable vertical scrolling
        "scrollCollapse": true, // enable collapsing footer if scrollY height not reached
        "serverSide": true,
        "stateDuration": 60 * 60 * 1, // set state saving duration to 1 hour
        "stateSave": true
    });

    // format search box
    dataTableSearch(false);
})



/**************************************
 * Event listeners
 **************************************/
/* edit custom user attribute */
$(".edit-custom-attribute").on("click", function(e) {
    e.stopImmediatePropagation();
    launchEditAttribute($(this));
/* for correct highlighting of sort glyphicon */
}).on("mouseenter", function() {
    $(this).parent().addClass("no-sort-highlight");
}).on("mouseleave", function() {
    $(this).parent().removeClass("no-sort-highlight");
});


/* display/hide warning depending on user upload option */
$("input[type=radio][name='user_spreadsheet_upload_options']").change(function() {
    if ($(this).val() == "safe") {
        $("#user-spreadsheet-upload-warning").stop(true, true).slideUp(200);
    } else {
        $("#user-spreadsheet-upload-warning").stop(true, true).slideDown(300);
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


/* populate file name when user upload spreadsheet selected */
$("#user-spreadsheet").on("change", function() {
    var file_name = $(this).val().replace(/.*\\/g, ''); // "C:\Users\Username\Desktop\file.xlsx"
    var file_path = $(this).val().replace(file_name, '');
    $("#user-spreadsheet-name").val(file_name);
})


/* prevent submission of user upload via enter key */
$("#user-spreadsheet-upload").on("keyup keypress", function(e) {
    var code = e.keyCode || e.which;
    if (code == 13) { // 13: enter
        e.preventDefault();
        return false;
    }
});


/* resize dataTable vertical scroll height on resize */
$(window).on("resize", function() {
    redrawDataTable();
});



/********************
 * Functions
 ********************/
/* submits for new user creation */
function addUser() {
    var cohort = $("#cohort-id").val();
    var phone_number = $("#phone-number").val().trim();
    // validation
    if (phone_number == "") {
        alert("Please enter an phone number.");
        return false;
    }
    showStatus(function() {
        // hide modal
        $("#add-user").modal("hide");
        // submit data
        post("/create_user", {
            "phone_number": phone_number,
            "cohort_id": cohort
        }, true);
        return $.Deferred();
    }, "Creating user", "User created", "Error: Unable to add user");
}


/********** this block also exists exactly the same way in survey_builder.js **********/
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
    // hide modal
    $("#add-attribute").modal("hide");
    // set up submit data
    data = {
        "cohort_id": cohortId,
        "new_attribute": newAttributeName.toLowerCase(),
        "default_value": defaultValue
    }
    // submit
    showStatus(function() {
        // submit data
        post("/create_user_attribute", data, true);
        return $.Deferred();
    }, "Creating user attribute", "User attribute created", "Error: Unable to create new user attribute");
}
/********** /this block also exists exactly the same way in survey_builder.js **********/


/* change user status from inactive to active */
function changeUserStatus(userId) {
    // hide change status modal
    var newStatus = $("#set-status-value").val();
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
            // reload table
            usersDataTable.api().ajax.reload(null, false);
            // redraw dataTable
            redrawDataTable();
        })
        // if fail
        .fail(function() {
            // undo changes
            document.execCommand("undo");
        });
    }, "Saving status", "Status saved", "Error: Status not saved");
}


/* changes user's timezone */
function changeUserTimezone(userId) {
    var attribute_name = "timezone";
    var new_value = $("#change-user-timezone-choices").val();
    // hide modal
    $("#change-user-timezone").modal("hide");
    showStatus(function() {
        return post("/set_user_attribute", {
            "attribute_name": attribute_name,
            "new_value": new_value,
            "user_id": userId
        }, false)
        // iff successful
        .done(function() {
            // reload table
            usersDataTable.api().ajax.reload(null, false);
            // redraw dataTable
            setTimeout(function() { redrawDataTable(); }, 100);
        });
    }, "Saving timezone", "Timezone saved", "Error: Timezone not saved");
}


/* runs search in data tables */
function dataTableSearch(search) {
    var text = $("#users_filter input").val();
    // if not empty, highlight
    if (text != "") {
        $("#users_filter input").css("background-color", "rgba(55, 208, 14, 0.34)");
    } else {
        $("#users_filter input").css("background-color", "#ffffff");
    }
    // if search, search
    if (search) {
        usersDataTable.fnFilter(text);
    }
}


/* deletes user */
function deleteUser(userId) {
    // hide change status modal
    $("#delete-user").modal("hide");
    showStatus(function() {
        // submit data
        return post("/set_user_attribute", {
            "attribute_name": "status",
            "new_value": "deleted",
            "user_id": userId
        }, false)
        // iff successful
        .done(function() {
            // reload table
            usersDataTable.api().ajax.reload(null, false);
            // redraw dataTable
            redrawDataTable();
        })
        // if fail
        .fail(function() {
            // undo changes
            document.execCommand("undo");
        })
    }, "Deleting user", "User deleted", "Error: Unable to delete user");
}


/* submits new user attribute for creation */
function editUserAttribute() {
    var newAttributeName = $("#edit-attribute-name").val().trim();
    var cohortId = $("#cohort-id").val();
    var newDefaultValue = $("#edit-default-value").val().trim();
    var previousAttributeName = $("#previous-attribute-name").val();
    var previousDefaultValue = $("#previous-default-value").val();
    // error checking
    if (newAttributeName == "") {
        alert("Please enter an attribute name.");
        return false;
    }
    if (newDefaultValue == "") {
        alert("Please enter a default value for this attribute.");
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
    // check for changes
    if ((newAttributeName == previousAttributeName) && (newDefaultValue == previousDefaultValue)) {
        alert("Please change either the attribute name or default value if you wish to edit this attribute.");
        return false;
    }
    // set up submit data
    data = {
        "cohort_id": cohortId,
        "new_attribute_name": newAttributeName.toLowerCase(),
        "new_default_value": newDefaultValue,
        "previous_attribute_name": previousAttributeName.toLowerCase(),
        "previous_default_value": previousDefaultValue
    }
    // hide modal
    $("#edit-user-attribute").modal("hide");
    // submit
    showStatus(function() {
        // submit data
        post("/edit_user_attribute", data, true);
        return $.Deferred();
    }, "Editing user attribute", "User attribute edited", "Error: Unable to edit user attribute");
}


/* Get scrollY offset height */
function getScrollYHeightOffset() {
    var height = $("#top-nav-container").outerHeight(true) +
                 $("#sub-nav-container").outerHeight(true) +
                 $("#users_wrapper > .row").outerHeight(true) +
                 $(".dataTables_scrollHead").outerHeight(true) +
                 $(".dataTables_scrollFoot").outerHeight(true) +
                 $(".dataTables_paginate").outerHeight(true) +
                 1; // bInfo .row div
    return height;
}


/********** this block also exists exactly the same way in survey_builder.js **********/
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
/********** /this block also exists exactly the same way in survey_builder.js **********/


/* launch add user modal */
function launchAddUser() {
    $("#add-user").modal("show");
    $("#phone-number").val("");
}


/* launches modal for changing time zone */
function launchChangeTimezone(userId, userPhoneNumber, currentTimezone) {
    // reset inputs
    resetInputs("change-user-timezone", [{ }]);
    // repopulate modal
    setModalProperties("change-user-timezone", {
        "title": "Change User '" + userPhoneNumber + "' Timezone",
        "buttonAction": "changeUserTimezone('" + userId + "')"
    });
    // populate modal
    $("#change-user-timezone-choices").val(currentTimezone);
    // currently set timezone
    $("#change-user-timezone").modal("show");
}

/* DUPLICATE CODE in message_sender.js START */
/* launches modal for changing user status (except delete, that's in its own function) */
function launchChangeUserStatus(userId, force) {
    var currentStatus = $("#" + userId + "-status").text();
    // stop if status is anything other than a changeable status
    if (currentStatus != "inactive" && currentStatus != "paused" && currentStatus != "active") {
        return false;
    }
    // populate modal with values
    setModalProperties("change-user-status", {
        "buttonAction": "changeUserStatus('" + userId + "')"
    });
    $("#change-user-status-phone-number").html(
        $("#users [data-column='phonenum'][data-objid='" + userId + "']").text()
    );
    if (currentStatus == "active") {
        $('#set-status-value option[value="active"]').attr("disabled", "disabled");
        $('#set-status-value option[value="paused"]').attr("selected", "selected");
        $("#change-user-status-pause-message, #change-user-status-message").show();
        $("#change-user-status-activate-message").hide();
    } else if (currentStatus == "paused") {
        $('#set-status-value option[value="active"]').attr("selected", "selected");
        $('#set-status-value option[value="paused"]').attr("disabled", "disabled");
        $("#change-user-status-activate-message, #change-user-status-message").show();
        $("#change-user-status-pause-message").hide();
    } else {
        $('#set-status-value option[value="active"]').attr("selected", "selected");
        $("#change-user-status-activate-message, #change-user-status-message").show();        
        $("#change-user-status-pause-message").hide();
    }
    if (force) {
        $("#change-user-status-pause-message, #change-user-status-activate-message, #change-user-status-message").hide();
    }
    // show modal
    $("#change-user-status").modal("show");
}
/* DUPLICATE CODE in message_sender.js END */

/* launches modal for deleting user */
function launchDeleteUser(userId) {
    // set modal properties
    setModalProperties("delete-user", {
        "buttonAction": "deleteUser('" + userId + "')"
    });
    // populate modal with values
    $("#delete-user-phone-number").html(
        $("#users [data-column='phonenum'][data-objid='" + userId + "']").text()
    );
    // show modal
    $("#delete-user").modal("show");
}


/* launches modal for editing custom user attributes */
function launchEditAttribute(element) {
    // populate modal with values
    $("#edit-attribute-name, #previous-attribute-name").val(element.attr("data-attribute"));
    $("#edit-default-value, #previous-default-value").val(element.attr("data-default"));
    // show modal
    $("#edit-user-attribute").modal("show");
}


/* launches modal for user upload */
function launchUploadUserSpreadsheet() {
    // reset all values in user upload modal
    resetInputs("upload-user-spreadsheet", [{"id": "user-spreadsheet-upload-options-safe", "default": true}]);
    // show modal
    $("#upload-user-spreadsheet").modal("show");
}


/* resize/redraws dataTable */
function redrawDataTable() {
    // adjust vertical height
    var newScrollYHeight = $(window).height() - SCROLL_Y_HEIGHT_OFFSET;
    usersDataTable.fnSettings().oScroll.sY = newScrollYHeight;
    // adjust column sizing
    usersDataTable.fnAdjustColumnSizing();
}


/* save contenteditable changes to database */
function saveContent(element) {
    var attributeName = element.attr("data-column");
    var newText = element.text().trim();
    var objectId = element.attr("data-objid");
    // prevent editing in same field until it's reloaded
    element.attr("contenteditable", false).removeClass("editable");
    // if the field is a phone number, add +1 to the beginning to match database
    if (attributeName == "phonenum") {
        newText = "+1" + newText;
    }
    // wrap with showStatus to show user status of request
    showStatus(function() {
        var $this = element;
        return post("/set_user_attribute", {
            "attribute_name": attributeName.toLowerCase(),
            "new_value": newText,
            "user_id": objectId
        }, false)
        // iff successful
        .done(function() {
            // reload table
            usersDataTable.api().ajax.reload(null, false);
            // redraw dataTable
            setTimeout(function() { redrawDataTable(); }, 100);
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


/* upload file for parsing */
function uploadUserSpreadsheet() {
    var filePath = $("#user-spreadsheet").val();
    var fileExtension = filePath.split('.').pop();
    // validation
    if (!filePath || filePath == "") {
        alert("Please select a file to upload");
        return false;
    } else if (!(fileExtension == "xls" || fileExtension == "xlsx" || fileExtension == "csv")) {
        alert("Please select a valid file (must be Excel or CSV file).");
        return false;
    }
    showStatus(function() {
        var formData = new FormData($("#user-spreadsheet-upload")[0]);
        // prevent things from being edited while uploading
        $("#overlay").fadeIn(300);
        // submit
        return $.ajax({
            "url": "/upload_user_file",
            "type": "POST",
            data: formData,
            cache: false,
            contentType: false,
            processData: false
        }).done(function(response) {
            // if reload is specified, reload
            if (response["reload"] == "true") {
                location.reload(true);
            }
            // hide modal
            $("#upload-user-spreadsheet").modal("hide");
            if (response["__status__"] == "true") {
                // refresh user tables
                usersDataTable.api().ajax.reload(null, false); // user paging is not reset on reload
                // reload no users alert
                $("#no-users-container-hidden").load(window.location.pathname + " #no-users-container > *", function() {
                    if ($(this).html().trim().length == 0) {
                        $("#no-users-container").slideUp(500);
                    }
                });
            } else if (response["__status__"] == "false") {
                var errorHTML = "";
                // collect errors
                if (("general" in response) && response["general"].length > 0) {
                    for (var i = 0, len = response["general"].length; i < len; i++) {
                        errorHTML += '<div class="alert alert-warning" role="alert">' +
                                        '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> ' +
                                        response["general"][i] +
                                     '</div>';
                    }
                }
                if (("headers" in response) && response["headers"].length > 0) {
                    errorHTML += '<div class="alert alert-warning" role="alert">' +
                                    '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> ' +
                                    'Column header errors. There seem to be problems with your column headers.' +
                                 '</div>' +
                                 '<ul>';
                    for (var i = 0, len = response["headers"].length; i < len; i++) {
                        errorHTML += '<li>' + response["headers"][i] + '</li>';
                    }
                    errorHTML += '</ul>';
                }
                if (("phone_number_repeats" in response) && response["phone_number_repeats"].length > 0) {
                    errorHTML += '<div class="alert alert-warning" role="alert">' +
                                    '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> ' +
                                    'Repeated phone numbers found. Phone numbers must be unique for each user.' +
                                 '</div>' +
                                 '<ul>';
                    for (var i = 0, len = response["phone_number_repeats"].length; i < len; i++) {
                        errorHTML += '<li>' + response["phone_number_repeats"][i] + '</li>';
                    }
                    errorHTML += '</ul>';
                }
                if (("bad_phonenumbers" in response) && response["bad_phonenumbers"].length > 0) {
                    errorHTML += '<div class="alert alert-warning" role="alert">' +
                                    '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> ' +
                                    'Invalid phone numbers. Phone numbers must comprise of 10 digits.' +
                                 '</div>' +
                                 '<ul>';
                    for (var i = 0, len = response["bad_phonenumbers"].length; i < len; i++) {
                        errorHTML += '<li>' + response["bad_phonenumbers"][i] + '</li>';
                    }
                    errorHTML += '</ul>';
                }
                if (("existing_users" in response) && response["existing_users"].length > 0) {
                    errorHTML += '<div class="alert alert-warning" role="alert">' +
                                    '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> ' +
                                    'Taken phone numbers. These phone numbers already exist in this cohort.' +
                                 '</div>' +
                                 '<ul>';
                    for (var i = 0, len = response["existing_users"].length; i < len; i++) {
                        errorHTML += '<li>' + response["existing_users"][i] + '</li>';
                    }
                    errorHTML += '</ul>';
                }
                if (("timezone_errors" in response) && response["timezone_errors"].length > 0) {
                    errorHTML += '<div class="alert alert-warning" role="alert">' +
                                    '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> ' +
                                    'Invalid timezone names were found (these are case-sensitive). ' +
                                    '<a href="/docs#380-timezone-names" target="_blank">Click here</a> ' +
                                    'for a list of all valid timezone names.' +
                                 '</div>' +
                                 '<ul>';
                    for (var i = 0, len = response["timezone_errors"].length; i < len; i++) {
                        errorHTML += '<li>' + response["timezone_errors"][i] + '</li>';
                    }
                    errorHTML += '</ul>';
                }
                if (("unknown" in response) && response["unknown"].length > 0) {
                    errorHTML += '<div class="alert alert-warning" role="alert">' +
                                    '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span> ' +
                                    'Unknown errors. These rows contain unknown errors.' +
                                 '</div>' +
                                 '<ul>';
                    for (var i = 0, len = response["unknown"].length; i < len; i++) {
                        errorHTML += '<li>' + response["unknown"][i] + '</li>';
                    }
                    errorHTML += '</ul>';
                }
                // populate modal
                $("#user-upload-errors-list").html(errorHTML);
                // show modal
                $("#user-upload-errors").modal("show");
            } else if (response["__status__"] == "reload") {
                $("#status-popup").hide();
                location.reload(true);
            } else {
                alert("Sorry, something went wrong and this page will refresh.")
                $("#status-popup").hide();
                location.reload(true);
            }
        }).always(function() {
            // reset file input so that onchange can capture same file
            $("#user-spreadsheet").val(null);
            // undo overlay so they can do things again
            $("#overlay").fadeOut(300);
        })
    }, "Uploading", "Uploaded", "Error: Unable to upload");
}


/* datatables plugin function to allow searching of phone numbers irrespective of formatting */
$.fn.DataTable.ext.type.search.phoneNumber = function(data) {
    return !data ? "" : typeof data === "string" ? data + data.replace(/[ \(\)\-]/g, "") : data;
};