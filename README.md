# API to manage email lists

A small Flask app to create and manage list of emails.
Saves entries in a database and can add them to a Mailchimp list

## Install

    $ git clone https://github.com/maximebf/maillistr.git
    $ cd maillistr
    $ pip install -r requirements.txt
    $ python maillistr.py init
    $ python maillistr.py run

Available on port 5000

## Configuration

### Mailchimp support

Set `MAILCHIMP = True` in settings.py and set your api key.

### Using Gevent to call Mailchimp API

Install gevent using `pip install gevent`.  
Set `USE_GEVENT = True` in settings.py.

## Usage

### Authentification

Use the generated api key as the HTTP username

    curl http://APIKEY:@example.com/

All request needs authentification unless specified

### Responses

Responses use JSON. The key "success" will always be present with a boolean value.
In case success is false, an "error" key will contain a string with the error message.

### List lists

Request:

    GET /

Response:

    {
        "success": true,
        "lists": [
            {
                "slug": "my_list",
                "mailchimp_list_id": "...",
                "added_at": "ISO 8601 date",
                "nb_entries": 0
            }
        ]
    }

### Create list

Request:

    POST /<list_slug>

Parameters:

 - `mailchimp_list_id`: id of a mailchimp list

### Delete list

Request:
    
    DELETE /<list_slug>

### Show list

Request:

    GET /<list_slug>

Response:

    {
        "success": true,
        "list": {
            "slug": "my_list",
            "mailchimp_list_id": "...",
            "added_at": "ISO 8601 date",
            "nb_entries": 0
        }
    }

### Add entry

Does NOT require authentification

Request:

    POST /<list_slug>/entries

Parameters:

 - `email`

### Add entry using JSONp

Does NOT require authentification

Request:

    GET /<list_slug>/entries/jsonp

Parameters:

 - `email`
 - `callback`

### List entries

Request:

    GET /<list_slug>/entries

Optional parameters:

 - `since`: a datetime string (many format supported)
 - `limit`: integer
 - `offset`: integer

Response;

    {
        "success": true,
        "nb_entries": 1,
        "nb_total": 1,
        "entries": [
            {
                "email": "example@example.com",
                "ip": "127.0.0.1",
                "added_at": "ISO 8601 date"
            }
        ]
    }

### List entries as CSV

Request:

    GET /<list_slug>/entries.csv

Same parameters as list entries