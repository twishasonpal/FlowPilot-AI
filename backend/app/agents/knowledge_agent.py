from ..services.knowledge import search

def retrieve(db, query):
    return {"evidence":search(db,query),"grounded":True}
