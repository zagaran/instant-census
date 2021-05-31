function send_message() {
    var message = $('#message').val();
    do_send(message);
}

function do_send(message) {
    $.post("/sendmessage", {'message': message}, function(data) {
        setTimeout(function() { location.reload();}, 1000);
    });
}