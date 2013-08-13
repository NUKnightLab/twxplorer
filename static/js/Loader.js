// Loader.js
//
// Class to "lazy load" data
//
// @target = jquery element
// @page_size = number of elements to load at a time
// @format_callback = called to generate HTML for each item
// @post_show_callback = called after each iteration of show_data
//
function Loader(target, page_size, format_callback, post_show_callback) {
    var _self = this;

    this.data = [];
    this.next_index = 0;
       
    this.set_data = function(data) {
        this.data = data;    
        this.next_index = 0;
    }
    
    this.show_data = function() {
        target.unbind('scroll.loader');

        var s = '';
        var max_index = Math.min(this.next_index+page_size, this.data.length);
    
        for(var i = this.next_index; i < max_index; i++) {
            s += format_callback(this.data[i]);
        } 
        this.next_index = i;

        target.find('.loading').remove();
        target.append(s);
       
        if(this.next_index < (this.data.length - 1)) {
            target.append('<div class="loading"><i class="icon-spinner icon-spin"></i></div>')
                .bind('scroll.loader', this.on_scroll)
        } 
    
        if(post_show_callback) {
            post_show_callback();
        }
    }
    
    this.on_scroll = function(event) {
        var offset = target.find('.loading').offset().top - target.offset().top;
        if(offset < target.innerHeight()) {
            _self.show_data();
        }    
    }
}
