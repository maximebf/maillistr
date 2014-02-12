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

## Usage

### Authentification

Use the generated api key as the HTTP username

    curl http://APIKEY:@example.com/

All request needs authentification unless specified

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

Request:

    POST /<list_slug>/entries

Parameters:

 - `email`

### List entries

Request:

    GET /<list_slug>/entries

Response;

    {
        "success": true,
        "entries": [
            {
                "email": "example@example.com",
                "ip": "127.0.0.1",
                "added_at": "ISO 8601 date",
                "added_to_mailchimp": true
            }
        ]
    }

### List entries as CSV

Request:

    GET /<list_slug>/entries.csv