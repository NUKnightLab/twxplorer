// utility.js
//

function show_progress(msg) {
    $('#progress_msg').html(msg);
    $('#progress_modal').modal('show');
}

function hide_progress() {
    $('#progress_modal').modal('hide');
}

function show_confirm(msg, callback) {
    $('#confirm_msg').html(msg);
    $('#confirm_modal .btn-primary').bind('click.confirm', function(event) {
        $(this).unbind('click.confirm');
        $('#confirm_modal').modal('hide');
        callback();
    });
    $('#confirm_modal').modal('show');
}

function show_error(error) {      
    if($('#error_alert').length) {
        $('#error_alert .error-msg').html(error);
    } else {        
        $('#control_bar').after(
            '<div id="error_alert" class="alert alert-danger">'
            + '<button type="button" class="close" data-dismiss="alert">&times;</button>'
            + '<span class="error-msg">'+error+'</span></div>'
        );
    }
}

function hide_error() {
    $('#error_alert').remove();
}

function do_ajax(url, data, on_error, on_success) {
    $.ajax({
        url: url,
        data: data,
        dataType: 'json',
        timeout: 45000, // ms
        error: function(xhr, status, err) {
            on_error(err || status);
        },
        success: function(data) {
            if(data.error) {
                on_error(data.error);
            } else {
                on_success(data);
            }
        }
    });
}
