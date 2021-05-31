/**************************************
 * Constants
 **************************************/
var RESPONSES = {};


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
    $("#users-cohort-option, #responses-cohort-option").html(cohortOptions).trigger("change");

    // trigger loading of default month view for messages report
    $(".messages-view-option[value='month']").trigger("click");

    // draw response time report
    showStatus(function() {
        return $.post("/_get_response_time_report_data", function(data) {
            drawResponseTimeReport(data);
        });
    }, "Generating data report", "Data report generated", "Error: Unable to generate data report");
});


/**************************************
 * Event listeners
 **************************************/
/* message report view option buttons */
$(".messages-view-option").on("click", function() {
    var time_range = $(this).val();
    // if this button is already active, don't do anything
    if ($(this).hasClass("active")) {
        return true;
    }
    // clear tooltips (since nvd3 fails at this)
    $(".nvtooltip").each(function() {
        $(this).remove();
    });
    // for all view buttons
    $(".messages-view-option").each(function() {
        $(this)
            // remove active class on this button
            .removeClass("active")
            // disable button
            .attr("disabled", true)
    });
    // for this button
    $(this)
        // add active class
        .addClass("active")
        // save current width
        .css("width", $(this).outerWidth())
        // replace with loading
        .html("<span class='glyphicon glyphicon-refresh spinning'></span>");
    // generate new view
    showStatus(function() {
        return $.post("/_get_messages_report_data", {
            "time_range": time_range
        }, function(data) {
            // draw report
            drawMessagesReport(data);
            // for all view buttons
            $(".messages-view-option").each(function() {
                // enable button
                $(this).removeAttr("disabled")
            });
            // replace previous text for active button
            var activeButton = $(".messages-view-option.active");
            activeButton.html(activeButton.attr("data-text"));
        });
    }, "Generating data report", "Data report generated", "Error: Unable to generate data report");
});


/* users report cohort option */
$("#users-cohort-option").on("change", function() {
    var cohortId = $(this).val();
    populateAttributeOptions(cohortId, "users-attribute-option");
});


/* responses report cohort option */
$("#responses-cohort-option").on("change", function() {
    var cohortId = $(this).val();
    // generate new view
    showStatus(function() {
        return $.post("/_get_responses_report_data", {
            "cohort_id": cohortId
        }, function(data) {
            RESPONSES = data["data"];
            populateQuestionOptions(RESPONSES);
        });
    }, "Generating data report", "Data report generated", "Error: Unable to generate data report");
});


/* response report question option */
$("#responses-question-option").on("change", function() {
    var questionId = $(this).val();
    // generate new view
    drawResponsesReport(RESPONSES, questionId);
});


/* users report attribute option */
$("#users-attribute-option").on("change", function() {
    var attribute = $(this).val();
    var cohortId = $("#users-cohort-option").val()
    // generate new view
    showStatus(function() {
        return $.post("/_get_users_report_data", {
            "cohort_id": cohortId
        }, function(data) {
            drawUserReport(data, attribute);
        });
    }, "Generating data report", "Data report generated", "Error: Unable to generate data report");
});


/**************************************
 * Draw Reports
 **************************************/
/* draws message report and associated information */
function drawMessagesReport(messagesReportData) {

    // format data for nvd3
    var data = [
        {
            "key": "Incoming Messages",
            "color": "#ff0000",
            "values": messagesReportData["incoming"]
        }, {
            "key": "Outgoing Messages",
            "color": "#00ff00",
            "values": messagesReportData["outgoing"]
        }, {
            "key": "All Messages",
            "color": "#0000ff",
            "values": messagesReportData["all"]
        }
    ]

    // draw graph
    nv.addGraph(function() {
        var chart = nv.models.lineChart()
            .useInteractiveGuideline(true)
            .options({
                interpolate: "monotone",
                margin: {
                    left: 100,
                    bottom: 100,
                },
                showLegend: true,
                showXAxis: true,
                showYAxis: true,
                transitionDuration: 500,
                xScale: d3.time.scale.utc(),
                x: function(d) { return moment.utc(d.time) },
                y: function(d) { return d.count },
            });
        chart.xAxis
            .axisLabel("Time")
            .rotateLabels(-45)
            .ticks(14)
            .tickFormat(function(d) { return moment.utc(d).format("M/DD hh:mma"); })
            ;
        chart.yAxis
            .axisLabel("Number of Messages")
            .tickFormat(d3.format("d"))
            .domain([0, d3.max(data, function(d) { return d.count })])
            ;
        applyChart("#messages-svg", chart, data, false, "transition");

        // update chart on window resize
        nv.utils.windowResize(function() { chart.update() });

        return chart;
    });

    // hide loading div
    $("#messages-panel .loading").hide();
}


/* draws responses report and associated information */
function drawResponsesReport(responsesReportData, questionId) {

    var responses = responsesReportData[questionId]["responses"]

    // format data for nvd3
    var data = [
        {
            "key": responsesReportData[questionId]["question_text"],
            "values": responses
        }
    ]

    // set graph width
    if (responses.length > 10) {
        var width = $(".svg-container").width() + ((responses.length - 10) * 100);
        $("#responses-svg").css("width", width);
    } else {
        $("#responses-svg").css("width", "100%");
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
            });
        chart.xAxis
            .axisLabel("Attribute Values")
            //.staggerLabels(true);
            ;
        chart.yAxis
            .axisLabel("Number of Responses")
            .ticks(10)
            .tickFormat(d3.format("d"))
            ;
        applyChart("#responses-svg", chart, data, true, "remove");

        // update chart on window resize
        nv.utils.windowResize(chart.update);

        return chart;
    });

    // hide loading div
    $("#responses-panel .loading").hide();
}

/* draws user report and associated information */
function drawResponseTimeReport(responseTimeReportData) {
    // populate total
    $("#questions-total").html(responseTimeReportData["expected"]);

    // format data for nvd3
    var data = [];
        //{
        //    "key": "Responses (number of)",
        //    "color": "#00ff00",
        //    "values": responseTimeReportData["response_times"]
        //}
    //]

    // make it aggregated
    var aggregated = JSON.parse(JSON.stringify(responseTimeReportData["response_times"])); // make a copy
    var arrayLength = aggregated.length;
    if (arrayLength > 0) {
        for (var i = 1; i < arrayLength; i++) {
            aggregated[i]["count"] += aggregated[i-1]["count"];
            aggregated[i-1]["count"] = 100 * aggregated[i-1]["count"] / responseTimeReportData["expected"];
        }
        aggregated[arrayLength-1]["count"] = 100 * aggregated[arrayLength-1]["count"] / responseTimeReportData["expected"]
    }

    // add aggregated data
    data.push(
        {
            "key": "Responses Times (aggregate)",
            "color": "#0000ff",
            "values": aggregated
        }
    );

    // draw graph
    nv.addGraph(function() {
        var chart = nv.models.lineWithFocusChart()
            .useInteractiveGuideline(true)
            .options({
                brushExtent: [0, 900],
                interpolate: "monotone",
                margin: {
                    left: 100,
                    bottom: 100,
                },
                showLegend: true,
                showXAxis: true,
                showYAxis: true,
                transitionDuration: 500,
                x: function(d) { return d.time },
                y: function(d) { return d.count },
                yDomain: [0, 100],
            });
        chart.xAxis
            .axisLabel("Response Time")
            .rotateLabels(-45)
            .tickFormat(formatMinutes)
            .ticks(15)
            ;
        chart.yAxis
            .axisLabel("% Response Rate")
            .tickFormat(d3.format("d"))
            .showMaxMin(true)
            ;
        chart.y2Axis
            .tickFormat(d3.format("d"))
            ;
        applyChart("#response-time-svg", chart, data, false, "remove");

        // update chart on window resize
        nv.utils.windowResize(function() { chart.update() });

        return chart;
    });

    // hide loading div
    $("#response-time-panel .loading").hide();
}


/* draws user report and associated information */
function drawUserReport(userReportData, attribute) {
    // populate total
    $("#users-total").html(userReportData["count"]);

    // format data for nvd3
    var data = [
        {
            "key": attribute.toUpperCase(),
            "values": userReportData[attribute]
        }
    ]

    // draw graph
    nv.addGraph(function() {
        var chart = nv.models.discreteBarChart()
            .options({
                staggerLabels: false,
                tooltips: true,
                transitionDuration: 500,
                x: function(d) { return d.label },
                y: function(d) { return d.count }
            });
        chart.xAxis
            .axisLabel("Attribute Values")
            ;
        chart.yAxis
            .axisLabel("Number of Users")
            .ticks(10)
            .tickFormat(d3.format("d"))
            ;
        applyChart("#users-svg", chart, data, true, "remove");

        // update chart on window resize
        nv.utils.windowResize(chart.update);

        return chart;
    });

    // hide loading div
    $("#users-panel .loading").hide();
}


/**************************************
 * Helper Functions
 **************************************/
/* formats time into "##h ##m ##s" */
function formatMinutes(d) {
    var hours = Math.floor(d / 3600),
        minutes = Math.floor((d - (hours * 3600)) / 60),
        seconds = d - (hours * 3600) - (minutes * 60);
    var output = seconds + 's';
    if (minutes) {
        output = minutes + 'm ' + output;
    }
    if (hours) {
        output = hours + 'h ' + output;
    }
    return output;
};


/* populates #attributeField with the attributes off Cohort(cohortId) */
function populateAttributeOptions(cohortId, attributeField) {
    var attributeOptions = "";
    var attributes = COHORTS[cohortId]["attributes"];
    for (var i = 0, iLength = attributes.length; i < iLength; i++) {
        attributeOptions += "<option value='" + attributes[i] + "'>" + attributes[i] + "</option>";
    }
    $("#" + attributeField).html(attributeOptions).trigger("change");
}


/* populates with available questions in cohort */
function populateQuestionOptions(questions) {
    var questionOptions = "";
    for (var key in questions) {
        if (questions.hasOwnProperty(key)) {
            questionOptions += "<option value='" + key + "'>" + questions[key]["question_text"] + "</option>";
        }
    }
    $("#responses-question-option").html(questionOptions).trigger("change");
}


/* checks if labels are overlapping and applies staggered labels if they are */
function fixOverlappingLabels(chart, labels) {
    var prev;
    labels.each(function(d, i) {
        // skip the first iteration
        if (i > 0) {
            // get bounding boxes
            var thisBounding = this.getBoundingClientRect();
            var prevBounding = prev.getBoundingClientRect();
            // if they overlap
            if (thisBounding.left < prevBounding.right) {
                chart.xAxis.staggerLabels(true);
                chart.update();
                return;
            }
        }
        prev = this;
    });
}


/* applies new chart */
function applyChart(selector, chart, data, fixLabels, transition) {
    // apply chart
    if (typeof transition === "undefined") {
        transition = "remove";
    }
    if (transition == "remove") {
        // remove previous chart data
        d3.select(selector)
            .selectAll("*").remove();
        // apply new data
        d3.select(selector)
            .datum(data)
            .call(chart)
            ;
    } else if (transition == "transition") {
        // apply new data
        d3.select(selector)
            .datum(data)
            .transition().duration(350)
            .call(chart)
            ;
    }
    // fix labels
    if (fixLabels) {
        // check if labels overlap
        var labels = d3.selectAll(selector + " .nv-x.nv-axis text:not(.nv-axislabel)");
        fixOverlappingLabels(chart, labels);
    }
}