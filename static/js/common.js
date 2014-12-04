// common.js

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
    $('#warning_alert').remove();
}

function show_progress(msg) {
    hide_error();
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

function show_warning(message) {
    if($('#warning_alert').length) {
        $('#warning_alert').html(message);
    } else {        
        $('#control_bar').after(
            '<div id="warning_alert" class="alert">'
            + '<button type="button" class="close" data-dismiss="alert">&times;</button>'
            + '<span class="error-msg">'+message+'</span></div>'
        );
    }
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

function add_filter(stem) {
    _filter.push(stem);
    filter_results(_session._id);
}

function remove_filter(stem) {
    var stem_index = $.inArray(stem, _filter);
    if(stem_index > -1) {
        _filter.splice(stem_index, 1);
    }
    filter_results(_session._id);
}

function clear_filters() {
    if(_filter.length > 0){
        _filter = []
        filter_results(_session._id);
    }
}

function show_filter() {   
    var s = '';
    
    if(_filter.length > 0) {
       s = '<li class="blank">&nbsp; Filters: </li>';
    }
    for(var i = 0; i < _filter.length; i++) {
        s += '<li>'+get_term(_filter[i])
            + '<button class="close" onclick="remove_filter(\''+_filter[i].replace("'", "\\&apos;")+'\');">&times;</button>'
            + '</li>';      
    }
    
    $('#filter_list').html(s).show();
}

// Get the term to represent filter item in UI
function get_term(s) {
    if(s[0] == '#') {
        return s;
    }   
    if(s in _url_map) {
        return _url_map[s];  
    }
    if(s in _session.stem_map) { 
        if(_session.stem_map[s].length > 1) {
            return _session.stem_map[s][0]+', ...';
        } 
        return _session.stem_map[s];
    }
    return s;
}

function unshare_snapshot() {
    $('#share').popover('hide');    
 
    show_progress('Unsharing snapshot');
   
    do_ajax('/history/update/'+_session._id+'/', 
        {shared: 0},
        function(error) {
            show_error('Error unsharing snapshot ('+error+')');
            hide_progress();
        },
        function(data) {  
            _session.shared = 0;
            hide_progress();
        }
    );        
}

function tweet_snapshot() {
    document.location.href = "/history/tweet/"+_session._id+'/';
}

function initialize() {
    //
    // #save handler
    //
    $('#save').click(function(event) {
        show_progress('Saving snapshot');
        
        do_ajax('/history/update/'+_session._id+'/', 
            {saved: 1},
            function(error) {
                show_error('Error saving snapshot ('+error+')');
                hide_progress();
             },
            function(data) {  
                _session.saved = 1; 
                hide_progress();
                $('#save').hide();
            }
        );
    });
    

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
                if(term_list && term_list.length > 1) {                
                    anchor = '<a data-toggle="tooltip" data-placement="right" data-title="'+term_list.join(', ')+'" data-trigger="hover">';
                } else {
                    anchor = '<a>';
                }
                               
                html += ''
                    + '<li class="term" onclick="add_filter(\''+stem.replace("'", "\\&apos;")+'\');">'
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
                var max_count =  _HashtagLoader.data[0][1];
                for(var i = 0; i < hashtag_counts.length; i++) {                   
                    hashtag = hashtag_counts[i][0];
                    count = hashtag_counts[i][1];
                    var pct = (count * 100)/max_count;
            
                    html += ''
                        + '<li class="term" onclick="add_filter(\''+hashtag+'\');">'
                        + '<span class="count">'+count+'</span>'
                        + '<div class="inner">'
                        + '<a>'+hashtag+'</a>'
                        + '<div class="bar" style="width: '+pct+'%;">&nbsp;</div>'
                        + '</div>'
                        + '</li>';     
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