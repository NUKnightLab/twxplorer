"""
dummy db class that does absolutely nothing
"""


def setup_env():
    """Setup the working environment as appropriate for loc, stg, prd."""  
    pass  
    
 
def setup():
    """Create the project database and user."""
    pass


def sync():
    pass


def seed(sample='n'):
    """
    Seed the database.  Set sample=y to load sample data (default = n).
    This needs to be run once per database, but has to be run from the
    app or work server, because we need to pip data to psql.
    """
    pass

    
def destroy():
    """Remove the database and user."""   
    pass    
    

