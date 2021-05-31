/**************************************
 * Constants
 **************************************/



/**************************************
 * $(window).load();
 **************************************/
$(window).load(function() {
    // fill in cohort options
    var cohortOptions = "";
    var cohortIds = Object.keys(COHORTS);
    // if no cohort data
    if (cohortIds.length == 0) {
        $(".loading").html("No data available.");
        $("button").each(function() {
            $(this).attr("disabled", true);
        });
        return false;
    }
    for (var i = 0, iLength = cohortIds.length; i < iLength; i++) {
        var cohortName = COHORTS[cohortIds[i]]["name"];
        cohortOptions += "<option value='" + cohortIds[i] + "'>" + cohortName + "</option>";
    }
    // trigger change of cohort options to initiate downstream functions
    $("#cohort-option").html(cohortOptions).trigger("change");

    // fill in question options
    var questionOptions = "";
    var questionIds = Object.keys(QUESTIONS);
    // if no question data
    if (questionIds.length == 0) {
        return false;
    }
    for (var i = 0, iLength = questionIds.length; i < iLength; i++) {
        var questionText = QUESTIONS[questionIds[i]];
        questionOptions += "<option value='" + questionIds[i] + "'>" + questionText + "</option>";
    }
    // trigger change of question options to initiate downstream functions
    $("#question-option-1, #question-option-2").html(questionOptions);
    $("#question-option-2 option:eq(1)").attr("selected", "selected");
    $("#question-option-1, #question-option-2").trigger("change");

    // draw response time report
    showStatus(function() {
        return $.post("/_get_users_report_data", {
            "cohort_id": $("#cohort-option").val()
        }, function(data) {
            drawUserReport(data, $("#attribute-option").val());
        });
    }, "Generating data report", "Data report generated", "Error: Unable to generate data report");
});


/**************************************
 * Event listeners
 **************************************/
/* cohort option */
$("#cohort-option").on("change", function() {
    var cohortId = $(this).val();
    populateAttributeOptions(cohortId, "attribute-option");
});


/* question option */
$("#question-option-1, #question-option-2").on("change", function() {
    var questionNumber = $(this).attr("id").slice(-1);
    var questionId = $(this).val();
    // populate question text
    $("#question-" + questionNumber + "-text").text(QUESTIONS[questionId]);
    // populate answers
    $.post("/_get_most_recent_responses", {
        "question_id": questionId
    }, function(data) {
        var responses = data["responses"];
        populateResponses(responses, questionNumber);
    });
})


/* attribute option */
$("#attribute-option").on("change", function() {
    var attribute = $(this).val();
    var cohortId = $("#cohort-option").val()
    // generate new view
    showStatus(function() {
        return $.post("/_get_users_report_data", {
            "cohort_id": $("#cohort-option").val()
        }, function(data) {
            drawUserReport(data, attribute);
        });
    }, "Generating data report", "Data report generated", "Error: Unable to generate data report");
});


var interval = setInterval(function() {
    // refresh graph
    $.post("/_get_users_report_data", {
        "cohort_id": $("#cohort-option").val()
    }, function(data) {
        drawUserReport(data, $("#attribute-option").val());
    });
    // refresh question 1 responses
    $.post("/_get_most_recent_responses", {
        "question_id": $("#question-option-1").val()
    }, function(data) {
        var responses = data["responses"];
        populateResponses(responses, 1);
    });
    // refresh question 2 responses
    $.post("/_get_most_recent_responses", {
        "question_id": $("#question-option-2").val()
    }, function(data) {
        var responses = data["responses"];
        populateResponses(responses, 2);
    });
}, 1000);


/**************************************
 * Functions
 **************************************/
/* draws user report and associated information */
function drawUserReport(userReportData, attribute) {

    // catch empty or null data and prettify
    for (var i = 0, iLength = userReportData[attribute].length; i < iLength; i++) {
        var label = userReportData[attribute][i]["label"];
        if (typeof label === "string" && label.trim() == "") {
            label = "(No Text)";
        } else if (label === null) {
            label = "(No Value)";
        }
        userReportData[attribute][i]["label"] = label.toString();
    }

    // sort data
    // localeCompare is only a function for type String
    var sortedData = userReportData[attribute].sort(function (a, b) {
        return a.label.toString().localeCompare(b.label.toString());
    });

    // crc demo-specific change
    var crcData = []
    if (attribute == "ENJOYMENT") {
        for (var i = 1; i <= 10; i++) {
            var label = i;
            var count = 0;
            for (var j = 0, jLength = sortedData.length; j < jLength; j++) {
                if (sortedData[j]["label"] == String(i)) {
                    count = sortedData[j]["count"];
                }
            }
            crcData.push({
                "label": String(i),
                "count": count
            })
        }
    } else {
        crcData = sortedData;
    }

    // format data for nvd3
    data = [
        {
            "key": attribute.toUpperCase(),
            "values": crcData
        }
    ]
    var maxY = Math.ceil(d3.max($.map(crcData, function(d) { return d.count; })));
    if (maxY < 10) {
        maxY = 10;
    } else {
        maxY = maxY + (5 - (maxY % 5));
    }

    // draw graph
    nv.addGraph(function() {
        var chart = nv.models.discreteBarChart()
            .options({
                staggerLabels: false,
                tooltips: true,
                transitionDuration: 500,
                x: function(d) { return d.label },
                y: function(d) { return d.count }
            })
            .forceY([0, maxY]);
        chart.xAxis
            ;
        chart.yAxis
            .ticks(10)
            .tickFormat(d3.format("d"))
            ;
        d3.select('#demo-svg')
            .datum(data)
            .call(chart)
            ;

        // update chart on window resize
        nv.utils.windowResize(chart.update);

        return chart;
    });

    // hide loading div
    $(".loading").hide();
}


/* populates #attributeField with the attributes off Cohort(cohortId) */
function populateAttributeOptions(cohortId, attributeField) {
    var attributeOptions = "";
    var attributes = COHORTS[cohortId]["attributes"];
    for (var i = 0, iLength = attributes.length; i < iLength; i++) {
        attributeOptions += "<option value='" + attributes[i] + "'>" + attributes[i] + "</option>";
    }
    $("#" + attributeField).html(attributeOptions).trigger("change");
}

/* populates question responses */
function populateResponses(responses, questionNumber) {
    var responseListHTML = "";
    for (var i = 0, iLength = responses.length; i < iLength; i++) {
        responseListHTML += "<li>" + responses[i] + "</li>";
    }
    $("#question-" + questionNumber + "-answers").html(responseListHTML);
}