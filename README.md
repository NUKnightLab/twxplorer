###Setup

Install [virtualenvwrapper](http://virtualenvwrapper.readthedocs.org/en/latest/).

Install [MongoDB](http://www.mongodb.org/downloads) and start the Mongo server by running `mongod` in the `bin` directory of your Mongo installation.

    # Clone repositories
    git clone git@github.com:NUKnightLab/secrets.git
    git clone git@github.com:NUKnightLab/fablib.git
    git clone git@github.com:NUKnightLab/twxplorer.git
    
    # Change into the twxplorer repository
    cd twxplorer
    
    # Make a virtual environment for twxplorer
    mkvirtualenv twxplorer
    
    # Activate the virtual environment (if necessary)
    workon twxplorer
    
    # Install requirements
    pip install -r requirements.txt
    
    # Download nltk stopwords (if necessary)
    python -m nltk.downloader stopwords
    
    # Start the Flask development server
    python api.py
    
Visit the the website at [http://127.0.0.1:5000](http://127.0.0.1:5000)

   
    
