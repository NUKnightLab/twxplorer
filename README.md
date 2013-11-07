###Setup

Install [virtualenvwrapper](http://virtualenvwrapper.readthedocs.org/en/latest/).

Install [MongoDB](http://www.mongodb.org/downloads) and start the Mongo server by running `mongod` in the `bin` directory of your Mongo installation.

    # Clone the secrets repository
    git clone git@github.com:NUKnightLab/secrets.git
    
    # Clone the twxplorer repository
    git clone git@github.com:NUKnightLab/twxplorer.git
    
    # Make a virtual environment for twxplorer
    mkvirtualenv twxplorer

    # Change into the twxplorer repository
    cd twxplorer
    
    # Activate the virtual environment (if necessary)
    workon twxplorer
    
    # Install requirements
    pip install -r requirements.txt

    # If compilation fails with lxml installation error, install both libxml2-dev and libxslt-dev
    apt-get install libxml2-dev libxslt-dev
    
    # Download nltk stopwords (if necessary)
    python -m nltk.downloader stopwords
    
    # Start the Flask development server
    python api.py
    
Visit the the website at [http://127.0.0.1:5000](http://127.0.0.1:5000)

   
    
