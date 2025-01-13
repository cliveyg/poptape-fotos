# poptape-fotos
Microservice to control photo resources written in Python Flask that uses MongoDB.

Please see [this gist](https://gist.github.com/cliveyg/cf77c295e18156ba74cda46949231d69) to see how this microservice works as part of the auction system software.

### API routes

```
/fotos [GET] (Unauthenticated)
Returns all the possible endpoints for the microservice. 
Possible return codes: [200]

```

#### Notes:
None

#### Rate limiting:
In addition most routes will return an HTTP status of 429 if too many requests are made in a certain space of time. The time frame is set on a route by route basis.

#### Tests:
Tests can be run from app root using: `pytest --cov-config=app/tests/.coveragerc --cov=app app/tests`

#### Docker:
This app can now be run in Docker using the included docker-compose.yml and Dockerfile. The database and roles still need to be created manually after successful deployment of the app in Docker. It's on the TODO list to automate these parts :-)

#### TODO:
* Most of it ;)
