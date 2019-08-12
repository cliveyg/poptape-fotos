# app/models.py

#-----------------------------------------------------------------------------#
# models pretty useless tbh
#-----------------------------------------------------------------------------#

class Foto():
    def __init__(self, name, description, owner, status, item_type):
        self.name = name
        self.description = description
        self.owner = owner
        self.status = status

