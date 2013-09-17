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

function initialize_loaders() {
    //
    // Loaders
    //
    _TermsLoader = new Loader($('#terms'), 20,
        function(stem_counts, callback) {  
            var html = '';
            var max_count =  _TermsLoader.data[0][1];
            
            for(var i = 0; i < stem_counts.length; i++) {                   
                var stem = stem_counts[i][0];
                var count = stem_counts[i][1];
                var pct = (count * 100)/max_count;
            
                term_list = _session.stem_map[stem];
                if(term_list.length > 1) {                
                    anchor = '<a data-toggle="tooltip" data-placement="right" data-title="'+term_list.join(', ')+'" data-trigger="hover">';
                } else {
                    anchor = '<a>';
                }
                
                html += ''
                    + '<li class="term" onclick="add_filter(\''+stem+'\');">'
                    + '<span class="count">'+count+'</span>'
                    + '<div class="inner">'
                    + anchor+get_term(stem, ', ')+'</a>'
                    + '<div class="bar" style="width: '+pct+'%;">&nbsp;</div>'
                    + '</div>'
                    + '</li>';     
            }            
            callback(html);       
        },
        function(count) {
            $('#terms a[data-toggle="tooltip"]').slice(-count).tooltip();        
        }
    );
 
    _HashtagLoader = new Loader($('#hashtags'), 20,
        function(hashtag_counts, callback) {
            var hashtag, count, html = '';
            
            if(hashtag_counts.length) {
                for(var i = 0; i < hashtag_counts.length; i++) {                   
                    hashtag = hashtag_counts[i][0];
                    count = hashtag_counts[i][1];
            
                    html += ''
                        + '<li><span class="count">'+count+'</span><a href="javascript:void(0);" onclick="add_filter(\''+hashtag+'\')">'
                        + hashtag+'</a></li>';
                }  
            } else {
                html = '<p class="msg">no hashtags found</p>';
            }          
            callback(html);       
        }
    );
    
    _TweetsLoader = new Loader($('#tweets'), 10, 
        function(tweets, callback) {
            var html = '';

            for(var i = 0; i < tweets.length; i++) {      
                var tweet = tweets[i];
                             
                html += ''
                    + '<blockquote class="twitter-tweet" data-conversation="none" data-cards="hidden">'
                    + '<p>'+tweet.text+'</p>&mdash; '+tweet.user_name + ' (@'+tweet.user_screen_name+')'
                    + '<a href="https://twitter.com/twitterapi/status/'+tweet.id_str+'">'+tweet.created_at+'</a>'               
                    + '</blockquote>';
                //html += '<p>'+tweet.id_str+'</p>';
            }
            callback(html);
        },
        function() {
            twttr.widgets.load();
        }
    );
    
    _UrlsLoader = new Loader($('#urls'), 6,
        function(url_counts, callback) {   
            var urls = $.map(url_counts, function(elem, i) { return elem[0]; });
            
            if(urls.length) {                  
                do_ajax("/urls/", 
                    {urls: urls},
                    function(error) {
                        show_error(error);
                        callback('');
                    },
                    function(data) {   
                        var info, html = '';
                    
                        for(var i = 0; i < data.info.length; i++) {
                            info = data.info[i];
                            
                            _url_map[info.url] = (info.title || info.url);
                            
                            html += ''
                                + '<li>'
                                + '<span class="count">'+url_counts[i][1]+'</span>'
                                + '<div>'
                                + '<a href="javascript:void(0);" onclick="add_filter(\''+info.url+'\');">'+ _url_map[info.url] +'</a>'
                                + '<a class="external-link" href="'+info.url+'" target="_blank" title="open url in new window">'
                                + '<i class="icon-external-link"></i></a>'
                                + '</div>';
                                + '</li>';
                        }
                    
                        callback(html);
                    }
                );
            } else {
                callback('<p class="msg">no urls found</p>');
            }                   
        }
    );
   
}