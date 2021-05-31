/***************************************
 * Fix for fixed header on top of anchor links
 ***************************************/
$(window).load(function() {
    setTimeout(removeLinkAnchor, 1);
});

$("a[href^='#']").on("click", function() {
    $($(this).attr("href")).addClass("link-anchor");
    setTimeout(removeLinkAnchor, 1);
});

function removeLinkAnchor() {
    $(".link-anchor").each(function() {
        $(this).removeClass("link-anchor");
    });
}


/**************************************
 * Event Listeners
 **************************************/
/* enable/disable submit button depending on agree checkbox */
$("#tos-checkbox").on("change", function() {
    if ($(this).is(":checked")) {
        $("#tos-submit").attr("disabled", false);
    } else {
        $("#tos-submit").attr("disabled", true);
    }
});