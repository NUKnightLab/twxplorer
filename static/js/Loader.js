// Loader.js
// Classes to "lazy load" data
//

//
// @target = jquery element
// @page_size = number of elements to load at a time
// @format_callback = called to generate HTML for page_size items
// @post_load_callback = called after each execution of load_more
//
function Loader(target, page_size, format_callback, post_load_callback) {
    this.data = [];
    this.next_index = 0;

    this.target = target;
    this.page_size = page_size;
    this.format_callback = format_callback;
    this.post_load_callback = post_load_callback || function(count) {};   
 }

Loader.prototype.set_data = function(data) {     
    this.data = data;    
    this.next_index = 0;      
    return this;
};

Loader.prototype.show_loading = function() {
    if(!this.target.find('.loading').length) {
        this.target.append('<div class="loading"><i class="icon-spinner icon-spin"></i></div>')
        .bind('scroll.loader', this.on_scroll.bind(this));
    }    
    return this;
};

Loader.prototype.set_html = function(html) {
    this.target.find('.loading').remove();
    this.target.append(html);
    
    if(this.next_index < (this.data.length - 1)) {
        this.show_loading();
    } 
}

Loader.prototype.on_scroll = function(event) {
    var loading = this.target.find('.loading');
    if(loading.length) {  
        var offset = loading.offset().top - this.target.offset().top;
        if(offset < this.target.innerHeight()) {
            this.load_more();
        }   
    } 
};

Loader.prototype.load_more = function() {    
    var _self = this; 
    this.target.unbind('scroll.loader');

    var start_index = this.next_index;
    var max_index = Math.min(start_index+this.page_size, this.data.length);
    var count = max_index - start_index;
    
    this.format_callback(
        this.data.slice(this.next_index, max_index),
        function(html) {
            _self.next_index = max_index;           
            _self.set_html(html);
            _self.post_load_callback(count);
        },
        this.next_index
    );
};
    