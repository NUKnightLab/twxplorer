// Loader.js
// Classes to "lazy load" data
//

//
// Loader()
// @target = jquery element
// @page_size = number of elements to load at a time
// @format_callback = called to generate HTML for each item
// @post_load_callback = called after each execution of load_more
//
function Loader(target, page_size, format_callback, post_load_callback) {
    this.data = [];
    this.next_index = 0;

    this.target = target;
    this.page_size = page_size;
    this.format_callback = format_callback;
    this.post_load_callback = post_load_callback || function() {};   
 }

Loader.prototype.set_data = function(data) {     
    this.data = data;    
    this.next_index = 0;      
    return this;
};

Loader.prototype.set_html = function(html) {
    this.target.find('.loading').remove();
    this.target.append(html);
    
    if(this.next_index < (this.data.length - 1)) {
        this.target.append('<div class="loading"><i class="icon-spinner icon-spin"></i></div>')
        .bind('scroll.loader', this.on_scroll.bind(this));
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
    this.target.unbind('scroll.loader');

    var html = '';
    var max_index = Math.min(this.next_index+this.page_size, this.data.length);

    while(this.next_index < max_index) {
        html += this.format_callback(this.data[this.next_index]);
        this.next_index++;
    }
    
    this.set_html(html);
    this.post_load_callback();    
    return this;
};
    

//
// AjaxLoader()
// @target = jquery element
// @page_size = number of elements to load at a time
// @format_callback = called to generate HTML for page_size items
// @post_load_callback = called after each execution of load_more
//

function AjaxLoader(target, page_size, format_callback, post_load_callback) {
    Loader.call(this, target, page_size, format_callback, post_load_callback);
}

AjaxLoader.prototype = Object.create(Loader.prototype);

AjaxLoader.prototype.constructor = AjaxLoader;

AjaxLoader.prototype.load_more = function() {
    var _self = this; 
    this.target.unbind('scroll.loader');

    var max_index = Math.min(this.next_index+this.page_size, this.data.length);
    
    this.format_callback(
        this.data.slice(this.next_index, max_index),
        function(html) {
            _self.next_index = max_index;           
            _self.set_html(html);
        }
    );
};
